import json
import os

from openai import BadRequestError, OpenAI
from sqlalchemy.orm import Session

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import TOOL_DEFINITIONS, execute_tool
from backend.services import product_service

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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
        "products": products[:8],
    }


def _search_fallback(db: Session, query: str) -> dict:
    products = product_service.search_products(db, query=query, limit=8)
    return _agent_response(
        _format_products_reply(query, products),
        [{"tool": "search_products", "args": {"query": query}}],
        products,
    )


def _call_llm(messages: list):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )


def run_agent(db: Session, user_id: str, message: str, max_turns: int = 5) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Current user_id for cart tools: {user_id}",
        },
        {"role": "user", "content": message},
    ]

    tools_used = []
    products: list[dict] = []

    for _ in range(max_turns):
        try:
            response = _call_llm(messages)
        except BadRequestError as exc:
            if "tool_use_failed" not in str(exc):
                raise
            messages.append({"role": "system", "content": TOOL_RETRY_HINT})
            try:
                response = _call_llm(messages)
            except BadRequestError:
                return _search_fallback(db, message.strip())

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
                "content": json.dumps(result),
            })

    return _agent_response(
        "I need more steps to finish this request. Please try a simpler question.",
        tools_used,
        products,
    )
