import os
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.jwt_utils import create_access_token
from backend.auth.passwords import hash_password, verify_password

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


def _verify_google_token(token: str) -> dict:
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as exc:
        raise ValueError(
            "Google login requires google-auth. Run: pip install google-auth"
        ) from exc

    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google login is not configured on the server")

    return google_id_token.verify_oauth2_token(
        token, google_requests.Request(), GOOGLE_CLIENT_ID
    )


def _row_to_user(row) -> dict:
    data = dict(row._mapping)
    data.pop("password_hash", None)
    return data


def get_user_by_id(db: Session, user_id: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT id, email, name, auth_provider, provider_id, created_at
            FROM users WHERE id = :id
        """),
        {"id": user_id},
    ).fetchone()
    return _row_to_user(row) if row else None


def register_with_email(db: Session, email: str, password: str, name: str | None) -> dict:
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email.lower()},
    ).fetchone()
    if existing:
        raise ValueError("Email already registered")

    user_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO users (id, email, name, password_hash, auth_provider)
            VALUES (:id, :email, :name, :password_hash, 'email')
        """),
        {
            "id": user_id,
            "email": email.lower(),
            "name": name or email.split("@")[0],
            "password_hash": hash_password(password),
        },
    )
    db.commit()
    user = get_user_by_id(db, user_id)
    token = create_access_token(user_id, email.lower())
    return {"access_token": token, "token_type": "bearer", "user": user}


def login_with_email(db: Session, email: str, password: str) -> dict:
    row = db.execute(
        text("""
            SELECT id, email, name, password_hash, auth_provider, provider_id, created_at
            FROM users WHERE email = :email
        """),
        {"email": email.lower()},
    ).fetchone()
    if not row or not row.password_hash:
        raise ValueError("Invalid email or password")
    if not verify_password(password, row.password_hash):
        raise ValueError("Invalid email or password")

    user = _row_to_user(row)
    token = create_access_token(row.id, row.email)
    return {"access_token": token, "token_type": "bearer", "user": user}


def login_with_google(db: Session, token: str) -> dict:
    idinfo = _verify_google_token(token)
    email = idinfo["email"].lower()
    name = idinfo.get("name") or email.split("@")[0]
    provider_id = idinfo["sub"]
    user = _upsert_oauth_user(db, "google", provider_id, email, name)
    access_token = create_access_token(user["id"], user["email"])
    return {"access_token": access_token, "token_type": "bearer", "user": user}


GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")


def _http_json(method: str, url: str, headers: dict | None = None, data: dict | None = None) -> dict:
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise ValueError(f"GitHub auth failed: {detail}") from exc


def login_with_github(db: Session, code: str, redirect_uri: str) -> dict:
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise ValueError("GitHub login is not configured on the server")

    token_data = _http_json(
        "POST",
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError(token_data.get("error_description", "GitHub token exchange failed"))

    auth_header = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    profile = _http_json("GET", "https://api.github.com/user", headers=auth_header)
    provider_id = str(profile.get("id", ""))
    name = profile.get("name") or profile.get("login") or "GitHub User"
    email = profile.get("email")

    if not email:
        emails = _http_json("GET", "https://api.github.com/user/emails", headers=auth_header)
        primary = next((e for e in emails if e.get("primary")), None)
        email = (primary or emails[0] if emails else {}).get("email")

    if not email or not provider_id:
        raise ValueError("Could not read email from GitHub account")

    user = _upsert_oauth_user(db, "github", provider_id, email.lower(), name)
    access_token_jwt = create_access_token(user["id"], user["email"])
    return {"access_token": access_token_jwt, "token_type": "bearer", "user": user}


def _upsert_oauth_user(
    db: Session,
    provider: str,
    provider_id: str,
    email: str,
    name: str,
) -> dict:
    row = db.execute(
        text("""
            SELECT id, email, name, auth_provider, provider_id, created_at
            FROM users
            WHERE auth_provider = :provider AND provider_id = :provider_id
        """),
        {"provider": provider, "provider_id": provider_id},
    ).fetchone()

    if row:
        return _row_to_user(row)

    by_email = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).fetchone()

    if by_email:
        db.execute(
            text("""
                UPDATE users
                SET auth_provider = :provider,
                    provider_id = :provider_id,
                    name = COALESCE(name, :name)
                WHERE id = :id
            """),
            {
                "id": by_email.id,
                "provider": provider,
                "provider_id": provider_id,
                "name": name,
            },
        )
        user_id = by_email.id
    else:
        user_id = str(uuid.uuid4())
        db.execute(
            text("""
                INSERT INTO users (id, email, name, auth_provider, provider_id)
                VALUES (:id, :email, :name, :provider, :provider_id)
            """),
            {
                "id": user_id,
                "email": email,
                "name": name,
                "provider": provider,
                "provider_id": provider_id,
            },
        )

    db.commit()
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Failed to create user")
    return user
