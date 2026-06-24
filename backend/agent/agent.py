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


def _format_products_reply(query: str, products: list) -> str:
    if not products:
        return f"No products found for \"{query}\". Try a different keyword like shorts, dress, or shoe."

    lines = [f'Here are products matching "{query}":', ""]
    for i, p in enumerate(products[:5], 1):
        title = p.get("title", "Unknown")
        price = p.get("price", "?")
        rating = p.get("average_rating") or "?"
        reviews = p.get("review_count") or 0
        pid = p.get("product_id", "")
        lines.append(f"{i}. {title} — LKR {price}, ★ {rating} ({reviews} reviews), ID: {pid}")
    return "\n".join(lines)


def _search_fallback(db: Session, query: str) -> dict:
    products = product_service.search_products(db, query=query, limit=5)
    return {
        "reply": _format_products_reply(query, products),
        "tools_used": [{"tool": "search_products", "args": {"query": query}}],
    }


def _call_llm(messages: list):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )


def run_agent(db: Session, user_id: str, message: str, max_turns: int = 5) -> dict:
    """
    Agent loop: LLM → tool calls → LLM → final answer.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Current user_id for cart tools: {user_id}",
        },
        {"role": "user", "content": message},
    ]

    tools_used = []

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
            return {
                "reply": msg.content or "",
                "tools_used": tools_used,
            }

        messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if name in {"add_to_cart", "remove_from_cart", "get_cart"}:
                args.setdefault("user_id", user_id)

            result = execute_tool(db, name, args)
            tools_used.append({"tool": name, "args": args})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return {
        "reply": "I need more steps to finish this request. Please try a simpler question.",
        "tools_used": tools_used,
    }
