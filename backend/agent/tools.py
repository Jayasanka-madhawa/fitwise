from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.services import product_service, review_service, cart_service

from langsmith import traceable


def _json_safe(obj):
    """Convert DB types for LLM JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj

def _object_schema(properties: dict, required: list[str] | None = None) -> dict:
    schema = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required is not None:
        schema["required"] = required
    return schema

# OpenAI tool definitions (no duplicate names — Groq rejects malformed tool lists)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by keyword, brand, department, and LKR price range.",
            "parameters": _object_schema({
                "query": {"type": "string", "description": "Search keyword e.g. shoe, dress, shorts"},
                "department_final": {"type": "string", "description": "women, men, unisex, girls, boys"},
                "brand": {"type": "string"},
                "min_price": {"type": "number", "description": "Min price in LKR"},
                "max_price": {"type": "number", "description": "Max price in LKR"},
                "limit": {"type": "integer", "description": "Max results, default 5"},
            }),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details for one product by product_id.",
            "parameters": _object_schema(
                {"product_id": {"type": "string"}},
                required=["product_id"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_most_reviewed_products",
            "description": "Products with highest review_count. Supports LKR price filters.",
            "parameters": _object_schema({
                "department_final": {"type": "string"},
                "min_price": {"type": "number", "description": "Min price in LKR"},
                "max_price": {"type": "number", "description": "Max price in LKR"},
                "limit": {"type": "integer", "description": "Max results, default 5"},
            }),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_best_popular_products",
            "description": "Best popular products by popularity_score.",
            "parameters": _object_schema({
                "department_final": {"type": "string"},
                "min_reviews": {"type": "integer", "description": "Minimum reviews, default 20"},
                "limit": {"type": "integer", "description": "Max results, default 5"},
            }),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare multiple products side by side.",
            "parameters": _object_schema(
                {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                required=["product_ids"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_reviews",
            "description": "Get raw customer reviews for a product.",
            "parameters": _object_schema(
                {
                    "product_id": {"type": "string"},
                    "limit": {"type": "integer", "description": "Max reviews, default 10"},
                },
                required=["product_id"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_reviews",
            "description": "Summarize pros/cons and complaints from reviews.",
            "parameters": _object_schema(
                {"product_id": {"type": "string"}},
                required=["product_id"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the user's cart.",
            "parameters": _object_schema(
                {
                    "user_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "description": "Default 1"},
                },
                required=["user_id", "product_id"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove a product from the user's cart.",
            "parameters": _object_schema(
                {
                    "user_id": {"type": "string"},
                    "product_id": {"type": "string"},
                },
                required=["user_id", "product_id"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart",
            "description": "Get cart contents and total in LKR.",
            "parameters": _object_schema(
                {"user_id": {"type": "string"}},
                required=["user_id"],
            ),
        },
    },
]

_SEARCH_KEYS = {"query", "department_final", "brand", "min_price", "max_price", "limit", "offset"}
_MOST_REVIEWED_KEYS = {"department_final", "min_price", "max_price", "limit"}
_BEST_POPULAR_KEYS = {"department_final", "min_reviews", "limit"}


def _pick_args(args: dict, allowed: set[str]) -> dict:
    return {k: v for k, v in args.items() if k in allowed and v is not None}

@traceable(name="execute_tool", run_type="tool")
def execute_tool(db: Session, name: str, args: dict):
    """Run one tool and return JSON-safe result."""
    args = dict(args or {})

    if name == "search_products":
        if "q" in args and "query" not in args:
            args["query"] = args.pop("q")
        result = product_service.search_products(db, **_pick_args(args, _SEARCH_KEYS))
    elif name == "get_product_details":
        result = product_service.get_product_details(db, args["product_id"])
    elif name == "get_most_reviewed_products":
        result = product_service.get_most_reviewed_products(
            db, **_pick_args(args, _MOST_REVIEWED_KEYS)
        )
    elif name == "get_best_popular_products":
        result = product_service.get_best_popular_products(
            db, **_pick_args(args, _BEST_POPULAR_KEYS)
        )
    elif name == "compare_products":
        result = product_service.compare_products(db, args["product_ids"])
    elif name == "get_product_reviews":
        result = review_service.get_product_reviews(
            db, args["product_id"], args.get("limit", 10)
        )
    elif name == "summarize_reviews":
        result = review_service.summarize_reviews(db, args["product_id"])
    elif name == "add_to_cart":
        result = cart_service.add_to_cart(
            db, args["user_id"], args["product_id"], args.get("quantity", 1)
        )
    elif name == "remove_from_cart":
        result = cart_service.remove_from_cart(
            db, args["user_id"], args["product_id"]
        )
    elif name == "get_cart":
        result = cart_service.get_cart(db, args["user_id"])
    else:
        result = {"error": f"Unknown tool: {name}"}

    return _json_safe(result)
