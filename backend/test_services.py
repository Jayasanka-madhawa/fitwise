from backend.database import SessionLocal
from backend.services import product_service, review_service, cart_service

db = SessionLocal()

# Get one product ID from DB
from sqlalchemy import text
pid = db.execute(text("SELECT product_id FROM products LIMIT 1")).scalar()
print("Product ID:", pid)

print("\n=== Details ===")
print(product_service.get_product_details(db, pid))

print("\n=== Search shoes ===")
print(product_service.search_products(db, query="shoe", max_price=25000, limit=3))

print("\n=== Review summary ===")
print(review_service.summarize_reviews(db, pid))

db.close()