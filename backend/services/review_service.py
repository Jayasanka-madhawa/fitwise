from sqlalchemy import text
from sqlalchemy.orm import Session

def get_product_reviews(db: Session, product_id: str, limit: int = 20):
    sql = text("""
        SELECT id, product_id, rating, review_title, review_text,
               helpful_vote, verified_purchase, review_time, user_id
        FROM reviews
        WHERE product_id = :product_id
        ORDER BY helpful_vote DESC, review_time DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(sql, {"product_id": product_id, "limit": limit}).fetchall()
    return [dict(r._mapping) for r in rows]

def summarize_reviews(db: Session, product_id: str, limit: int = 50):
    reviews = get_product_reviews(db, product_id, limit=limit)
    if not reviews:
        return {
            "product_id": product_id,
            "summary": "No reviews available.",
            "total_sampled": 0,
        }

    ratings = [float(r["rating"]) for r in reviews if r["rating"] is not None]
    negative = [r for r in reviews if r["rating"] is not None and float(r["rating"]) <= 2]
    positive = [r for r in reviews if r["rating"] is not None and float(r["rating"]) >= 4]

    return {
        "product_id": product_id,
        "total_sampled": len(reviews),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "positive_count": len(positive),
        "negative_count": len(negative),
        "sample_complaints": [
            (r["review_text"] or "")[:300] for r in negative[:3]
        ],
        "sample_praise": [
            (r["review_text"] or "")[:300] for r in positive[:3]
        ],
    }