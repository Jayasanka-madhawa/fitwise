import json
import os

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import TOOL_DEFINITIONS, execute_tool

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        # Final text reply (no more tools)
        if not msg.tool_calls:
            return {
                "reply": msg.content or "",
                "tools_used": tools_used,
            }

        # Append assistant message with tool calls
        messages.append(msg)

        # Execute each tool
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            # Default user_id for cart if LLM forgets
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