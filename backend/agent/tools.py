import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.services import product_service, review_service, cart_service

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

# OpenAI tool definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by text, brand, department, and LKR price range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text e.g. shoe, dress, black"},
                    "department_final": {"type": "string", "description": "women, men, unisex, girls, boys"},
                    "brand": {"type": "string"},
                    "min_price": {"type": "number", "description": "Min price in LKR"},
                    "max_price": {"type": "number", "description": "Max price in LKR"},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details for one product by product_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_most_reviewed_products",
            "description": "Products with highest review_count (most famous).",
            "parameters": {
                "type": "object",
                "properties": {
                    "department_final": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_best_popular_products",
            "description": "Best popular products by popularity_score (rating × log reviews).",
            "parameters": {
                "type": "object",
                "properties": {
                    "department_final": {"type": "string"},
                    "min_reviews": {"type": "integer", "default": 20},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare multiple products side by side.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["product_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_reviews",
            "description": "Get raw customer reviews for a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_reviews",
            "description": "Summarize pros/cons and complaints from reviews.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the user's cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "default": 1},
                },
                "required": ["user_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove a product from the user's cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "product_id": {"type": "string"},
                },
                "required": ["user_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart",
            "description": "Get cart contents and total in LKR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                },
                "required": ["user_id"],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "get_most_reviewed_products",
        "description": "Products with highest review_count. Supports LKR price filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "department_final": {"type": "string"},
                "min_price": {"type": "number", "description": "Min price in LKR"},
                "max_price": {"type": "number", "description": "Max price in LKR"},
                "limit": {"type": "integer", "default": 5},
            },
        },
    },
},
]

def execute_tool(db: Session, name: str, args: dict):
    """Run one tool and return JSON-safe result."""
    if name == "search_products":
        result = product_service.search_products(db, **args)
    elif name == "get_product_details":
        result = product_service.get_product_details(db, args["product_id"])
    elif name == "get_most_reviewed_products":
        result = product_service.get_most_reviewed_products(db, **args)
    elif name == "get_best_popular_products":
        result = product_service.get_best_popular_products(db, **args)
    elif name == "compare_products":
        result = product_service.compare_products(db, args["product_ids"])
    elif name == "get_product_reviews":
        result = review_service.get_product_reviews(db, **args)
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