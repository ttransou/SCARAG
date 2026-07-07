from __future__ import annotations

from typing import Any


def generate_answer(
    query: str,
    context: list[dict[str, Any]],
    *,
    mode: str = "extractive",
    tabular_intent: bool = False,
) -> str:
    """Generate an answer constrained to retrieved evidence.

    Modes:
    - extractive: build concise summary from retrieved snippets.
    - mock: deterministic response for offline validation.
    - live: provider hook placeholder until implementation integration.
    """
    if mode == "live":
        return (
            "Live generation mode is enabled, but no provider adapter is configured yet. "
            "Connect a provider-specific implementation for production inference."
        )

    if mode == "mock":
        return f"[mock] SCARAG received query: {query}"

    if not context:
        return "I cannot answer confidently because no supporting evidence was retrieved."

    if tabular_intent and not any(bool(item.get("is_tabular")) for item in context):
        return (
            "I cannot provide a row-grounded tabular answer because no matching table evidence "
            "was retrieved."
        )

    snippets = [str(item.get("text", "")).strip() for item in context if str(item.get("text", "")).strip()]
    if not snippets:
        return "I cannot answer confidently because retrieved evidence had no usable content."

    summary_lines = snippets[:3]
    return "\n".join(summary_lines)
