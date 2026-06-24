from sqlalchemy import text
from sqlalchemy.orm import Session

def add_to_cart(db: Session, user_id: str, product_id: str, quantity: int = 1):
    sql = text("""
        INSERT INTO cart_items (user_id, product_id, quantity)
        VALUES (:user_id, :product_id, :quantity)
        ON CONFLICT (user_id, product_id)
        DO UPDATE SET quantity = cart_items.quantity + EXCLUDED.quantity
        RETURNING id, user_id, product_id, quantity
    """)
    row = db.execute(
        sql,
        {"user_id": user_id, "product_id": product_id, "quantity": quantity},
    ).fetchone()
    db.commit()
    return dict(row._mapping)

def remove_from_cart(db: Session, user_id: str, product_id: str):
    sql = text("""
        DELETE FROM cart_items
        WHERE user_id = :user_id AND product_id = :product_id
        RETURNING id
    """)
    row = db.execute(sql, {"user_id": user_id, "product_id": product_id}).fetchone()
    db.commit()
    return {"removed": row is not None}

def get_cart(db: Session, user_id: str):
    sql = text("""
        SELECT
            c.product_id,
            c.quantity,
            p.title,
            p.brand,
            p.price,
            p.currency,
            p.image_url,
            (c.quantity * p.price) AS line_total
        FROM cart_items c
        JOIN products p ON p.product_id = c.product_id
        WHERE c.user_id = :user_id
        ORDER BY c.added_at DESC
    """)
    rows = db.execute(sql, {"user_id": user_id}).fetchall()
    items = [dict(r._mapping) for r in rows]
    total = sum(float(i["line_total"]) for i in items)
    return {
        "user_id": user_id,
        "item_count": sum(i["quantity"] for i in items),
        "total_lkr": round(total, 2),
        "items": items,
    }