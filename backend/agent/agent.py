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
PRODUCTS_INDEX_MARKERS = ("[Products:", "[Products shown:")

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

CURRENCY_WORDS = frozenset({"rs", "lkr", "lk", "rupee", "rupees"})

WEAK_SEARCH_QUERIES = frozenset({"", "rs", "lkr", "product", "products", "item", "items", "thing", "things"})

PRICE_UNDER = re.compile(
    r"(?:under|below|less\s+than|max|upto|up\s+to|within)\s*"
    r"(?:lkr|rs|lkr)?\s*([0-9][0-9,]*)",
    re.IGNORECASE,
)
PRICE_OVER = re.compile(
    r"(?:over|above|more\s+than|min|at\s+least)\s*"
    r"(?:lkr|rs|lkr)?\s*([0-9][0-9,]*)",
    re.IGNORECASE,
)

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

TOOL_NAMES = frozenset({
    "search_products",
    "get_product_details",
    "get_most_reviewed_products",
    "get_best_popular_products",
    "compare_products",
    "get_product_reviews",
    "summarize_reviews",
    "add_to_cart",
    "remove_from_cart",
    "get_cart",
})

SEARCH_TOOLS = frozenset({
    "search_products",
    "get_most_reviewed_products",
    "get_best_popular_products",
})

PSEUDO_TOOL_PATTERNS = (
    re.compile(
        r"<function=(?P<name>[a-z_]+)>\s*(?P<args>\{.*\})\s*(?:</function>)?",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>search_products|get_product_details|get_most_reviewed_products|"
        r"get_best_popular_products|compare_products|get_product_reviews|summarize_reviews|"
        r"add_to_cart|remove_from_cart|get_cart)\s*>\s*(?P<args>\{.*\})",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>search_products|get_product_details|get_most_reviewed_products|"
        r"get_best_popular_products|compare_products|get_product_reviews|summarize_reviews|"
        r"add_to_cart|remove_from_cart|get_cart)\s*\(\s*(?P<args>\{.*\})\s*\)",
        re.DOTALL | re.IGNORECASE,
    ),
)

SHOPPING_HINT = re.compile(
    r"\b(watch|watches|shoe|shoes|dress|shirt|shorts|bag|jewelry|jacket|"
    r"buy|find|search|show me|looking for|want|need)\b",
    re.IGNORECASE,
)

GREETING_TOKENS = frozenset({
    "hi", "hey", "hello", "howdy", "greetings", "greeting", "sup", "yo",
    "ayubowan", "morning", "evening", "afternoon",
})

GREETING_PHRASE = re.compile(
    r"^(?:"
    r"(?:hi+|hey+|hello+|howdy|greetings?|sup|yo|ayubowan)"
    r"|good\s+(?:morning|afternoon|evening)"
    r"|what'?s\s+up"
    r")[!.?\s]*$",
    re.IGNORECASE,
)

GREETING_REPLY = (
    "Ayubowan! Welcome to FitWise. How can I help you with fashion shopping today?"
)


def _is_greeting_token(word: str) -> bool:
    token = word.lower()
    if token in GREETING_TOKENS:
        return True
    return bool(re.fullmatch(r"hi+", token) or re.fullmatch(r"hey+", token))


def _is_greeting(message: str) -> bool:
    text = message.strip()
    if not text:
        return False
    if GREETING_PHRASE.match(text):
        return True
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return False
    if not any(_is_greeting_token(w) for w in words):
        return False
    meaningful = [
        w for w in words
        if not _is_greeting_token(w) and w not in FILLER_WORDS and w not in CURRENCY_WORDS
    ]
    return not meaningful


def _greeting_response() -> dict:
    return _agent_response(GREETING_REPLY, [], [])


def _should_run_product_search(message: str, args: dict) -> bool:
    if _is_greeting(message):
        return False
    query = str(args.get("query") or "").strip().lower()
    if not query or query in WEAK_SEARCH_QUERIES:
        return bool(_keyword_candidates(message)) or bool(SHOPPING_HINT.search(message))
    if _is_greeting_token(query) or _is_greeting(query):
        return False
    return True


def _parse_price_number(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except (TypeError, ValueError):
        return None


def _extract_price_filters(message: str) -> dict:
    filters: dict = {}
    under = PRICE_UNDER.search(message)
    if under:
        value = _parse_price_number(under.group(1))
        if value is not None:
            filters["max_price"] = value
    over = PRICE_OVER.search(message)
    if over:
        value = _parse_price_number(over.group(1))
        if value is not None:
            filters["min_price"] = value
    return filters


def _is_price_refinement(message: str) -> bool:
    if not _extract_price_filters(message):
        return False
    return not _keyword_candidates(message)


def _prior_product_query(history: list[dict] | None, exclude_message: str = "") -> str | None:
    if not history:
        return None
    for item in reversed(history):
        if item.get("role") != "user":
            continue
        content = (item.get("content") or "").strip()
        if not content or content == exclude_message.strip():
            continue
        for keyword in _keyword_candidates(content):
            return keyword
    return None


def _format_filtered_reply(query: str, products: list, filters: dict) -> str:
    if not products:
        if filters.get("max_price") is not None:
            return (
                f'No {query} found under {int(filters["max_price"]):,} LKR. '
                "Try a higher budget or a different keyword."
            )
        if filters.get("min_price") is not None:
            return f'No {query} found above {int(filters["min_price"]):,} LKR.'
        return _format_products_reply(query, products)
    if filters.get("max_price") is not None:
        return f'Here are {len(products)} {query} options under {int(filters["max_price"]):,} LKR:'
    if filters.get("min_price") is not None:
        return f'Here are {len(products)} {query} options from {int(filters["min_price"]):,} LKR:'
    return _format_products_reply(query, products)


def _contextual_search(
    db: Session,
    message: str,
    history: list[dict] | None,
) -> dict | None:
    if not _is_price_refinement(message):
        return None
    query = _prior_product_query(history, exclude_message=message)
    if not query:
        return None
    filters = _extract_price_filters(message)
    products = product_service.search_products(db, query=query, limit=8, **filters)
    args = {"query": query, **filters}
    return _agent_response(
        _format_filtered_reply(query, products, filters),
        [{"tool": "search_products", "args": args}],
        products,
    )


def _fix_search_args(args: dict, message: str, history: list[dict] | None) -> dict:
    args = _sanitize_tool_args(args)
    query = str(args.get("query") or "").strip().lower()
    if query in WEAK_SEARCH_QUERIES or query.isdigit():
        prior = _prior_product_query(history, exclude_message=message)
        if prior:
            args["query"] = prior
    price_filters = _extract_price_filters(message)
    for key, value in price_filters.items():
        args.setdefault(key, value)
    return args


def _sanitize_tool_args(args: dict) -> dict:
    cleaned = dict(args or {})
    if cleaned.get("department_final") in {None, "", "unknown"}:
        cleaned.pop("department_final", None)
    return cleaned


def _parse_pseudo_tool_call(content: str) -> tuple[str, dict] | None:
    """Groq sometimes emits tool calls as plain text instead of tool_calls."""
    if not content:
        return None
    text = content.strip()
    for pattern in PSEUDO_TOOL_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        name = match.group("name").lower()
        if name not in TOOL_NAMES:
            continue
        try:
            args = _sanitize_tool_args(json.loads(match.group("args")))
        except json.JSONDecodeError:
            continue
        return name, args
    return None


def _looks_like_product_search(message: str) -> bool:
    if _is_greeting(message):
        return False
    return bool(SHOPPING_HINT.search(message)) or bool(_keyword_candidates(message))


def _reply_after_tool(name: str, args: dict, message: str, products: list[dict]) -> str:
    if name == "search_products":
        query = args.get("query") or _extract_search_query(message)
        price_filters = {
            k: args[k]
            for k in ("min_price", "max_price")
            if args.get(k) is not None
        }
        if price_filters:
            return _format_filtered_reply(query, products, price_filters)
        return _format_products_reply(query, products)
    if name in SEARCH_TOOLS:
        return _format_products_reply(message, products)
    if name == "compare_products" and products:
        return f"Here is a comparison of {len(products)} products:"
    if name == "get_product_details" and products:
        return f"Details for {products[0].get('title', 'this product')}:"
    return "Here's what I found:"


def _execute_parsed_tool(
    db: Session,
    user_id: str,
    name: str,
    args: dict,
    message: str,
    tools_used: list,
    products: list[dict],
) -> dict | None:
    if name == "search_products" and not _should_run_product_search(message, args):
        if _is_greeting(message):
            return _greeting_response()
        return None

    if name in {"add_to_cart", "remove_from_cart", "get_cart"}:
        args.setdefault("user_id", user_id)

    result = execute_tool(db, name, args)
    tools_used.append({"tool": name, "args": args})

    if name in PRODUCT_TOOLS:
        products[:] = _merge_products(products, _extract_products(name, result))

    if name in SEARCH_TOOLS or (name in PRODUCT_TOOLS and products):
        return _agent_response(
            _reply_after_tool(name, args, message, products),
            tools_used,
            products,
        )
    return None


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
    if _is_greeting(message):
        return []
    words = re.findall(r"[a-z0-9]+", message.lower())
    keywords = [
        w for w in words
        if w not in FILLER_WORDS
        and w not in CURRENCY_WORDS
        and not _is_greeting_token(w)
        and len(w) > 1
        and not w.isdigit()
    ]
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


def _search_fallback(
    db: Session,
    query: str,
    note: str | None = None,
    history: list[dict] | None = None,
) -> dict:
    if _is_greeting(query):
        return _greeting_response()

    contextual = _contextual_search(db, query, history)
    if contextual:
        if note:
            contextual["reply"] = f"{note}\n\n{contextual['reply']}"
        return contextual

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


def _rate_limit_fallback(db: Session, message: str, history: list[dict] | None = None) -> dict:
    return _search_fallback(
        db,
        message,
        note=(
            "AI is on Groq’s daily limit — showing direct search results. "
            "Full assistant chat returns after the limit resets."
        ),
        history=history,
    )


def _call_llm(messages: list):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )


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

    contextual = _contextual_search(db, message, history)
    if contextual:
        return contextual

    for _ in range(max_turns):
        try:
            response = _call_llm(messages)
        except Exception as exc:
            if is_rate_limit_error(exc):
                return _rate_limit_fallback(db, message, history)
            if not isinstance(exc, BadRequestError):
                raise
            if "tool_use_failed" not in str(exc):
                raise
            messages.append({"role": "system", "content": TOOL_RETRY_HINT})
            try:
                response = _call_llm(messages)
            except Exception as retry_exc:
                if is_rate_limit_error(retry_exc):
                    return _rate_limit_fallback(db, message, history)
                if isinstance(retry_exc, BadRequestError):
                    return _search_fallback(db, message, history=history)
                raise

        msg = response.choices[0].message

        if not msg.tool_calls:
            content = msg.content or ""
            parsed = _parse_pseudo_tool_call(content)
            if parsed:
                name, args = parsed
                if name == "search_products":
                    args = _fix_search_args(args, message, history)
                handled = _execute_parsed_tool(
                    db, user_id, name, args, message, tools_used, products
                )
                if handled:
                    return handled
            if not products and _looks_like_product_search(message):
                return _search_fallback(db, message, history=history)
            if _is_greeting(message) and not products:
                if content.strip():
                    return _agent_response(content, tools_used, products)
                return _greeting_response()
            return _agent_response(content, tools_used, products)

        messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            if name == "search_products":
                args = _fix_search_args(args, message, history)
                if not _should_run_product_search(message, args):
                    if _is_greeting(message):
                        return _greeting_response()
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps([]),
                    })
                    continue
            else:
                args = _sanitize_tool_args(args)

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
