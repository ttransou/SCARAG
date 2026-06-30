from __future__ import annotations

from typing import Any


def generate_answer(query: str, context: list[dict[str, Any]]) -> str:
    """Generate a simple grounded answer from retrieved context."""
    if not context:
        return "No supporting context was available."

    snippets = [str(item.get("text", "")).strip() for item in context if str(item.get("text", "")).strip()]
    joined = "\n".join(snippets[:3])
    return f"Based on the retrieved context, here is a draft answer to '{query}':\n{joined}"
