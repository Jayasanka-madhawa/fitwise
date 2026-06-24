import os
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://fitwise:fitwise@localhost:5432/fitwise"
engine = create_engine(DATABASE_URL)

with open("scripts/schema.sql") as f:
    with engine.begin() as conn:
        conn.execute(text(f.read()))

products = pd.read_csv("data/full/products_priced_full.csv")
reviews = pd.read_csv("data/full/reviews_priced_full.csv")

products.to_sql("products", engine, if_exists="append", index=False, chunksize=2000)
reviews.to_sql("reviews", engine, if_exists="append", index=False, chunksize=5000)

print("Done:", len(products), "products,", len(reviews), "reviews")