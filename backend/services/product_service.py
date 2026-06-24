from sqlalchemy import text
from sqlalchemy.orm import Session

PRODUCT_COLUMNS = """
    product_id, title, brand, department, department_final,
    price_usd, price, currency, average_rating, review_count,
    popularity_score, features, description, image_url, main_category
"""

def _row_to_dict(row):
    return dict(row._mapping)

def get_product_details(db: Session, product_id: str):
    sql = text(f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products
        WHERE product_id = :product_id
    """)
    row = db.execute(sql, {"product_id": product_id}).fetchone()
    if not row:
        return None
    return _row_to_dict(row)

def search_products(
    db: Session,
    query: str | None = None,
    department_final: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 10,
):
    conditions = ["1=1"]
    params = {"limit": limit}

    if query:
        conditions.append("""
            (title ILIKE :q OR brand ILIKE :q OR features ILIKE :q)
        """)
        params["q"] = f"%{query}%"

    if department_final and department_final != "unknown":
        conditions.append("department_final = :dept")
        params["dept"] = department_final

    if brand:
        conditions.append("brand ILIKE :brand")
        params["brand"] = f"%{brand}%"

    if min_price is not None:
        conditions.append("price >= :min_price")
        params["min_price"] = min_price

    if max_price is not None:
        conditions.append("price <= :max_price")
        params["max_price"] = max_price

    where_clause = " AND ".join(conditions)
    sql = text(f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products
        WHERE {where_clause}
        ORDER BY popularity_score DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]

def get_most_reviewed_products(
    db: Session,
    department_final: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 10,
):
    conditions = ["1=1"]
    params = {"limit": limit}
    if department_final and department_final != "unknown":
        conditions.append("department_final = :dept")
        params["dept"] = department_final
    if min_price is not None:
        conditions.append("price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        conditions.append("price <= :max_price")
        params["max_price"] = max_price
    where_clause = " AND ".join(conditions)
    sql = text(f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products
        WHERE {where_clause}
        ORDER BY review_count DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]

def get_best_popular_products(
    db: Session,
    department_final: str | None = None,
    min_reviews: int = 20,
    limit: int = 10,
):
    conditions = ["review_count >= :min_reviews"]
    params = {"limit": limit, "min_reviews": min_reviews}

    if department_final and department_final != "unknown":
        conditions.append("department_final = :dept")
        params["dept"] = department_final

    where_clause = " AND ".join(conditions)
    sql = text(f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products
        WHERE {where_clause}
        ORDER BY popularity_score DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]

def compare_products(db: Session, product_ids: list[str]):
    if not product_ids:
        return []
    sql = text(f"""
        SELECT {PRODUCT_COLUMNS}
        FROM products
        WHERE product_id = ANY(:ids)
    """)
    rows = db.execute(sql, {"ids": product_ids}).fetchall()
    by_id = {r.product_id: _row_to_dict(r) for r in rows}
    return [by_id[pid] for pid in product_ids if pid in by_id]

