#!/usr/bin/env python3
"""Truncate and reload products + reviews from CSV into Postgres."""
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://fitwise:fitwise@localhost:5432/fitwise",
)
PRODUCTS_CSV = ROOT / "data/full/products_priced_full.csv"
REVIEWS_CSV = ROOT / "data/full/reviews_priced_full.csv"


def main() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE reviews, cart_items, products CASCADE"))
        conn.execute(
            text("ALTER TABLE products ADD COLUMN IF NOT EXISTS product_category TEXT")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_products_product_category "
                "ON products(product_category)"
            )
        )

    products = pd.read_csv(PRODUCTS_CSV)
    reviews = pd.read_csv(REVIEWS_CSV)

    products.to_sql("products", engine, if_exists="append", index=False, chunksize=2000)
    reviews.to_sql("reviews", engine, if_exists="append", index=False, chunksize=5000)

    with engine.connect() as conn:
        product_count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        dept_rows = conn.execute(
            text("""
                SELECT department_final, COUNT(*) AS n
                FROM products
                WHERE department_final != 'unknown'
                GROUP BY department_final
                ORDER BY n DESC
            """)
        ).fetchall()

    print(f"Reload OK: {product_count:,} products, {len(reviews):,} reviews")
    print("UI departments:")
    for row in dept_rows:
        print(f"  {row.department_final}: {row.n:,}")


if __name__ == "__main__":
    main()
