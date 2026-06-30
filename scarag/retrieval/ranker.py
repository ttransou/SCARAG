from __future__ import annotations

from collections import Counter
from typing import Any


def rank_chunks(query: str, chunks: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    """Rank chunks by a simple token-overlap heuristic.

    This mirrors the README's intent for a lightweight local retrieval baseline
    before more advanced hybrid retrieval is introduced.
    """
    query_terms = {term.lower() for term in query.split() if term}
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        text = str(chunk.get("text", "")).lower()
        counter = Counter(text.split())
        overlap = sum(counter[term] for term in query_terms if term in counter)
        scored.append((float(overlap), chunk))

    ranked = [chunk for _, chunk in sorted(scored, key=lambda item: item[0], reverse=True)]
    return ranked[:top_k]
