from fastapi import FastAPI, Depends, HTTPException, Query, Request
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import BadRequestError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.database import get_db
from backend.services import product_service, review_service, cart_service
from backend.agent.agent import run_agent
from backend.auth import auth_service
from backend.auth.dependencies import get_current_user, get_optional_user


app = FastAPI(title="FitWise API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal server error"},
    )

# --- Auth schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

class GitHubLoginRequest(BaseModel):
    code: str
    redirect_uri: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# --- Product schemas ---
class CompareRequest(BaseModel):
    product_ids: list[str]

class CartAddRequest(BaseModel):
    product_id: str
    quantity: int = 1

class CartRemoveRequest(BaseModel):
    product_id: str

# --- Auth routes ---
@app.post("/auth/register", response_model=AuthResponse)
def auth_register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.register_with_email(db, body.email, body.password, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/auth/login", response_model=AuthResponse)
def auth_login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.login_with_email(db, body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

@app.post("/auth/google", response_model=AuthResponse)
def auth_google(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.login_with_google(db, body.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/auth/github", response_model=AuthResponse)
def auth_github(body: GitHubLoginRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.login_with_github(db, body.code, body.redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/auth/providers")
def auth_providers():
    return {
        "google": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "github": bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")),
    }

@app.get("/auth/config")
def auth_config():
    """Public OAuth client IDs for the frontend (Google client ID is not secret)."""
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "github_client_id": os.getenv("GITHUB_CLIENT_ID", ""),
    }

@app.get("/auth/me")
def auth_me(user: dict = Depends(get_current_user)):
    return user

# --- Product routes ---
@app.get("/products/departments")
def list_departments(db: Session = Depends(get_db)):
    return product_service.get_departments(db)

@app.get("/products/search")
def search_products(
    q: str | None = None,
    department_final: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = Query(default=24, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return product_service.search_products(
        db, query=q, department_final=department_final,
        brand=brand, min_price=min_price, max_price=max_price,
        limit=limit, offset=offset,
    )

@app.get("/products/most-reviewed")
def most_reviewed(
    department_final: str | None = None,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
):
    return product_service.get_most_reviewed_products(db, department_final, limit)

@app.get("/products/best-popular")
def best_popular(
    department_final: str | None = None,
    min_reviews: int = 20,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
):
    return product_service.get_best_popular_products(
        db, department_final, min_reviews, limit
    )

@app.get("/products/{product_id}")
def product_details(product_id: str, db: Session = Depends(get_db)):
    product = product_service.get_product_details(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products/compare")
def compare_products(body: CompareRequest, db: Session = Depends(get_db)):
    return product_service.compare_products(db, body.product_ids)

@app.get("/products/{product_id}/reviews")
def product_reviews(
    product_id: str,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    return review_service.get_product_reviews(db, product_id, limit)

@app.get("/products/{product_id}/reviews-summary")
def reviews_summary(product_id: str, db: Session = Depends(get_db)):
    return review_service.summarize_reviews(db, product_id)

# --- Cart routes (auth required) ---
@app.post("/cart/add")
def cart_add(
    body: CartAddRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return cart_service.add_to_cart(db, user["id"], body.product_id, body.quantity)

@app.delete("/cart/remove")
def cart_remove(
    body: CartRemoveRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return cart_service.remove_from_cart(db, user["id"], body.product_id)

@app.get("/cart/me")
def cart_get_me(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return cart_service.get_cart(db, user["id"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    tools_used: list
    products: list = []

@app.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    user_id = user["id"] if user else "guest"
    try:
        result = run_agent(db, user_id, body.message)
        return result
    except HTTPException:
        raise
    except BadRequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="FitWise assistant could not process that request. Try rephrasing, e.g. 'search for shorts'.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get("/health")
def health():
    return {"status": "ok"}
