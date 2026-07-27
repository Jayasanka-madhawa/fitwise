# FitWise Deployment Guide

Production stack: **Vercel** (frontend) + **Render** (backend) + **Neon** (Postgres).

Local development stays unchanged — separate DB and env files.

## Architecture

```
Production:
  fitwise.vercel.app  →  Render API  →  Neon Postgres  →  Groq

Local:
  localhost:3000      →  localhost:8001  →  Docker fitwise-db :5432
```

---

## Step 1 — Push to GitHub

```bash
git add .
git commit -m "Add deployment config"
git push origin main
```

---

## Step 2 — Neon (production database)

1. Create project at [neon.tech](https://neon.tech)
2. Copy connection string and convert for SQLAlchemy:
   ```
   postgresql+psycopg2://user:pass@host/neondb?sslmode=require
   ```
3. Load schema + data from your Mac (one time):

```bash
conda activate dl_env
export DATABASE_URL="postgresql+psycopg2://...@...neon.tech/neondb?sslmode=require"

python -c "
from sqlalchemy import create_engine, text
engine = create_engine('$DATABASE_URL')
with engine.begin() as c:
    c.execute(text(open('scripts/schema.sql').read()))
print('Schema OK')
"

python scripts/run_auth_migration.py
python scripts/reload_catalog.py
```

---

## Step 3 — Render (backend)

1. [render.com](https://render.com) → **New Web Service** → connect repo
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. **Environment variables:**

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Neon URL with `?sslmode=require` |
| `GROQ_API_KEY` | Your Groq key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` |
| `JWT_SECRET` | Long random string |
| `FRONTEND_URL` | `https://YOUR-APP.vercel.app` |
| `GOOGLE_CLIENT_ID` | Optional |
| `GITHUB_CLIENT_ID` | Optional |
| `GITHUB_CLIENT_SECRET` | Optional |

5. Test: `curl https://YOUR-API.onrender.com/health`

Or use the included `render.yaml` blueprint.

---

## Step 4 — Vercel (frontend)

1. [vercel.com](https://vercel.com) → import repo
2. **Root directory:** `frontend`
3. **Environment variable:**

```
NEXT_PUBLIC_API_URL=https://YOUR-API.onrender.com
```

4. Deploy → open your Vercel URL

---

## Step 5 — OAuth (optional)

Register **both** local and production URLs:

| Provider | URL |
|----------|-----|
| Google authorized origin | `https://YOUR-APP.vercel.app` |
| GitHub callback | `https://YOUR-APP.vercel.app/login/github/callback` |

---

## Local development (after deploy)

Nothing changes locally:

```bash
docker start fitwise-db
conda activate dl_env
uvicorn backend.main:app --reload --reload-dir backend --host 127.0.0.1 --port 8001

cd frontend && npm run dev
```

| File | Local value |
|------|-------------|
| `.env` | `DATABASE_URL=...@localhost:5432/fitwise` |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=http://localhost:8001` |

**Never commit** `.env` or `.env.local`.

---

## Updating production after code changes

```bash
git push origin main
```

Vercel and Render auto-redeploy. To refresh prod data only:

```bash
export DATABASE_URL="neon-url-here"
python scripts/reload_catalog.py
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS error on Vercel | Set `FRONTEND_URL` on Render to exact Vercel URL |
| Empty products | Run `reload_catalog.py` against Neon |
| Slow first load | Render free tier cold start (~30–60s) |
| AI rate limit | Groq free tier; search bar still works |
