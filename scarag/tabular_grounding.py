from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in _tokenize(query)
        if len(token) > 1 and token not in _STOPWORDS
    }


def _parse_tabular_lines(text: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if not lines:
        return "", []
    if len(lines) == 1:
        return lines[0], []
    return lines[0], lines[1:]


def apply_tabular_grounding(
    query: str,
    ranked_chunks: list[dict[str, Any]],
    *,
    tabular_intent: bool,
    min_row_term_matches: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not tabular_intent:
        return ranked_chunks, {
            "tabular_intent": False,
            "candidates": len(ranked_chunks),
            "matched_chunks": 0,
            "matched_rows": 0,
        }

    query_terms = _query_terms(query)
    if not query_terms:
        return [], {
            "tabular_intent": True,
            "candidates": len(ranked_chunks),
            "matched_chunks": 0,
            "matched_rows": 0,
            "reason": "no_query_terms",
        }

    grounded: list[dict[str, Any]] = []
    total_rows = 0
    for chunk in ranked_chunks:
        if not bool(chunk.get("is_tabular")):
            continue

        header, rows = _parse_tabular_lines(str(chunk.get("text", "")))
        if not rows:
            continue

        matched_rows: list[dict[str, Any]] = []
        for row in rows:
            row_terms = set(_tokenize(row))
            header_terms = set(_tokenize(header))
            matched_terms = sorted((row_terms | header_terms) & query_terms)
            if len(matched_terms) >= min_row_term_matches:
                matched_rows.append(
                    {
                        "row_text": row,
                        "matched_terms": matched_terms,
                    }
                )

        if not matched_rows:
            continue

        total_rows += len(matched_rows)
        grounded_chunk = dict(chunk)
        grounded_chunk["tabular_grounded"] = True
        grounded_chunk["matched_rows"] = matched_rows
        grounded_chunk["matched_row_count"] = len(matched_rows)
        grounded_chunk["matched_terms"] = sorted({term for row in matched_rows for term in row["matched_terms"]})
        grounded.append(grounded_chunk)

    trace = {
        "tabular_intent": True,
        "candidates": len(ranked_chunks),
        "matched_chunks": len(grounded),
        "matched_rows": total_rows,
    }
    if not grounded:
        trace["reason"] = "no_matched_rows"

    return grounded, trace
