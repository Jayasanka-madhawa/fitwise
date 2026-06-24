from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import BadRequestError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import product_service, review_service, cart_service
from backend.agent.agent import run_agent


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal server error"},
    )

# --- Schemas ---
class CompareRequest(BaseModel):
    product_ids: list[str]

class CartAddRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int = 1

class CartRemoveRequest(BaseModel):
    user_id: str
    product_id: str

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

# --- Cart routes ---
@app.post("/cart/add")
def cart_add(body: CartAddRequest, db: Session = Depends(get_db)):
    return cart_service.add_to_cart(db, body.user_id, body.product_id, body.quantity)

@app.delete("/cart/remove")
def cart_remove(body: CartRemoveRequest, db: Session = Depends(get_db)):
    return cart_service.remove_from_cart(db, body.user_id, body.product_id)

@app.get("/cart/{user_id}")
def cart_get(user_id: str, db: Session = Depends(get_db)):
    return cart_service.get_cart(db, user_id)

class ChatRequest(BaseModel):
    user_id: str = "guest"
    message: str

class ChatResponse(BaseModel):
    reply: str
    tools_used: list

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        result = run_agent(db, body.user_id, body.message)
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