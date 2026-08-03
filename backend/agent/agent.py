import json
import os
import re

from openai import APIStatusError, BadRequestError, OpenAI, RateLimitError
from sqlalchemy.orm import Session

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import TOOL_DEFINITIONS, _json_safe, execute_tool
from backend.services import product_service

from langsmith import traceable
from langsmith.wrappers import wrap_openai

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CHARS = 400

FILLER_WORDS = frozenset({
    "a", "an", "the", "for", "me", "my", "your", "we", "our", "us",
    "i", "am", "is", "are", "was", "be", "been", "being", "do", "does", "did",
    "can", "could", "would", "should", "will", "may", "might", "must",
    "you", "he", "she", "it", "they", "them", "this", "that", "these", "those",
    "please", "some", "any", "show", "find", "search", "suggest", "recommend",
    "looking", "look", "want", "need", "what", "about", "give", "get", "help", "with",
    "buy", "purchase", "order", "shop", "shopping", "see", "tell", "know",
    "something", "thing", "things", "items", "item", "product", "products", "stuff",
    "to", "of", "in", "on", "at", "from", "into", "up", "down", "out", "off", "over",
    "under", "between", "through", "during", "before", "after", "above", "below",
    "and", "or", "but", "so", "if", "when", "where", "how", "why", "which", "who",
    "hi", "hello", "thanks", "thank", "ok", "okay", "yes", "no", "yeah",
    "fitwise", "just", "also", "really", "very", "good", "best", "nice", "new",
    "like", "love", "interested", "thinking", "maybe", "someone",
})

TOOL_RETRY_HINT = (
    "Your last tool call was invalid. Call tools with valid JSON arguments only. "
    "For keyword search use search_products with {\"query\": \"keyword\"}."
)

PRODUCT_TOOLS = {
    "search_products",
    "get_most_reviewed_products",
    "get_best_popular_products",
    "compare_products",
    "get_product_details",
}


def _extract_products(tool_name: str, result) -> list[dict]:
    if tool_name == "get_product_details":
        if isinstance(result, dict) and result.get("product_id"):
            return [result]
        return []
    if isinstance(result, list):
        return [p for p in result if isinstance(p, dict) and p.get("product_id")]
    return []


def _merge_products(existing: list[dict], new_items: list[dict], limit: int = 8) -> list[dict]:
    seen = {p["product_id"] for p in existing}
    for item in new_items:
        pid = item.get("product_id")
        if pid and pid not in seen:
            existing.append(item)
            seen.add(pid)
        if len(existing) >= limit:
            break
    return existing[:limit]


def _format_products_reply(query: str, products: list) -> str:
    if not products:
        return f'No products found for "{query}". Try a different keyword like shorts, dress, or shoe.'
    return f'Here are {len(products)} products matching "{query}":'


def _agent_response(reply: str, tools_used: list, products: list[dict]) -> dict:
    return {
        "reply": reply,
        "tools_used": tools_used,
        "products": _json_safe(products[:8]),
    }


def is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code == 429:
        return True
    text = str(exc).lower()
    return "rate_limit" in text or "rate limit" in text


def _keyword_candidates(message: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", message.lower())
    keywords = [w for w in words if w not in FILLER_WORDS and len(w) > 1]
    if not keywords:
        stripped = message.strip()
        return [stripped] if stripped else []
    # Prefer longer, more specific terms (e.g. "watch" over "buy")
    unique = list(dict.fromkeys(keywords))
    unique.sort(key=len, reverse=True)
    return unique


def _extract_search_query(message: str) -> str:
    candidates = _keyword_candidates(message)
    return " ".join(candidates) if candidates else message.strip()


def _slim_product(product: dict) -> dict:
    return {
        "product_id": product.get("product_id"),
        "title": product.get("title"),
        "brand": product.get("brand"),
        "price": product.get("price"),
        "currency": product.get("currency"),
        "average_rating": product.get("average_rating"),
        "review_count": product.get("review_count"),
        "department_final": product.get("department_final"),
    }


def _slim_tool_result(name: str, result) -> object:
    if name == "get_product_details" and isinstance(result, dict):
        return _slim_product(result)
    if name in PRODUCT_TOOLS and isinstance(result, list):
        return [_slim_product(p) for p in result[:8] if isinstance(p, dict)]
    if name == "get_cart" and isinstance(result, dict):
        items = result.get("items") or []
        return {
            "item_count": result.get("item_count"),
            "total_lkr": result.get("total_lkr"),
            "items": [
                {
                    "product_id": i.get("product_id"),
                    "title": i.get("title"),
                    "quantity": i.get("quantity"),
                    "price": i.get("price"),
                }
                for i in items[:10]
            ],
        }
    return result


def _search_fallback(db: Session, query: str, note: str | None = None) -> dict:
    candidates = _keyword_candidates(query)
    search_query = " ".join(candidates) if candidates else query.strip()
    products = product_service.search_products(db, query=search_query, limit=8)

    if not products and candidates:
        for kw in candidates:
            products = product_service.search_products(db, query=kw, limit=8)
            if products:
                search_query = kw
                break

    reply = _format_products_reply(search_query, products)
    if note:
        reply = f"{note}\n\n{reply}"
    return _agent_response(
        reply,
        [{"tool": "search_products", "args": {"query": search_query}}],
        products,
    )


def _rate_limit_fallback(db: Session, message: str) -> dict:
    return _search_fallback(
        db,
        message,
        note=(
            "AI is on Groq’s daily limit — showing direct search results. "
            "Full assistant chat returns after the limit resets."
        ),
    )


def _call_llm(messages: list):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )


MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CHARS = 400
PRODUCTS_INDEX_MARKERS = ("[Products:", "[Products shown:")


def _truncate_history_content(content: str, max_chars: int) -> str:
    """Trim long replies but always keep the compact [Products: ...] index block."""
    marker_idx = -1
    for marker in PRODUCTS_INDEX_MARKERS:
        idx = content.find(marker)
        if idx != -1 and (marker_idx == -1 or idx < marker_idx):
            marker_idx = idx

    if marker_idx == -1:
        if len(content) > max_chars:
            return content[:max_chars] + "…"
        return content

    prefix = content[:marker_idx].rstrip()
    index_block = content[marker_idx:].strip()
    if len(prefix) > max_chars:
        prefix = prefix[:max_chars] + "…"
    return f"{prefix}\n{index_block}" if prefix else index_block


def _normalize_history(history: list[dict] | None) -> list[dict]:
    """Keep recent user/assistant turns for follow-up context."""
    if not history:
        return []

    normalized: list[dict] = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            content = _truncate_history_content(content, MAX_HISTORY_CHARS)
            normalized.append({"role": role, "content": content})
    return normalized

@traceable(name="fitwise_agent", run_type="chain")
def run_agent(
    db: Session,
    user_id: str,
    message: str,
    history: list[dict] | None = None,
    max_turns: int = 5,
) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Current user_id for cart tools: {user_id}",
        },
        *_normalize_history(history),
        {"role": "user", "content": message},
    ]

    tools_used = []
    products: list[dict] = []

    for _ in range(max_turns):
        try:
            response = _call_llm(messages)
        except Exception as exc:
            if is_rate_limit_error(exc):
                return _rate_limit_fallback(db, message)
            if not isinstance(exc, BadRequestError):
                raise
            if "tool_use_failed" not in str(exc):
                raise
            messages.append({"role": "system", "content": TOOL_RETRY_HINT})
            try:
                response = _call_llm(messages)
            except Exception as retry_exc:
                if is_rate_limit_error(retry_exc):
                    return _rate_limit_fallback(db, message)
                if isinstance(retry_exc, BadRequestError):
                    return _search_fallback(db, message)
                raise

        msg = response.choices[0].message

        if not msg.tool_calls:
            return _agent_response(msg.content or "", tools_used, products)

        messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if name in {"add_to_cart", "remove_from_cart", "get_cart"}:
                args.setdefault("user_id", user_id)

            result = execute_tool(db, name, args)
            tools_used.append({"tool": name, "args": args})

            if name in PRODUCT_TOOLS:
                products = _merge_products(products, _extract_products(name, result))

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(_slim_tool_result(name, result)),
            })

    return _agent_response(
        "I need more steps to finish this request. Please try a simpler question.",
        tools_used,
        products,
    )
