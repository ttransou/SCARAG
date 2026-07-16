from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class GenerationResult:
    text: str
    abstained: bool
    reason_code: str | None
    cited_chunk_ids: list[str]
    used_context_count: int
    grounding_policy: str


def _normalize_chunk_id(chunk: dict[str, Any]) -> str | None:
    value = str(chunk.get("chunk_id", "")).strip()
    return value or None


def _unique_chunk_ids(chunks: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for chunk in chunks:
        chunk_id = _normalize_chunk_id(chunk)
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        ordered.append(chunk_id)
    return ordered


def _has_citable_text(chunk: dict[str, Any]) -> bool:
    text = str(chunk.get("text", "")).strip()
    if len(text) < 10:
        return False
    return len(_TOKEN_RE.findall(text)) >= 2


def generate_answer_result(
    query: str,
    context: list[dict[str, Any]],
    *,
    mode: str = "extractive",
    tabular_intent: bool = False,
) -> GenerationResult:
    """Generate an answer constrained to retrieved evidence and record how it was grounded.

    Modes:
    - extractive: build concise summary from retrieved snippets.
    - mock: deterministic response for offline validation.
    - live: provider hook placeholder until implementation integration.
    """
    if mode == "live":
        return GenerationResult(
            text=(
                "Live generation mode is enabled, but no provider adapter is configured yet. "
                "Connect a provider-specific implementation for production inference."
            ),
            abstained=False,
            reason_code="live_adapter_unconfigured",
            cited_chunk_ids=[],
            used_context_count=0,
            grounding_policy="implementation_hook",
        )

    if mode == "mock":
        return GenerationResult(
            text=f"[mock] SCARAG received query: {query}",
            abstained=False,
            reason_code=None,
            cited_chunk_ids=_unique_chunk_ids(context[:3]),
            used_context_count=min(3, len(context)),
            grounding_policy="mock_passthrough",
        )

    if tabular_intent:
        if not context:
            return GenerationResult(
                text=(
                    "I cannot provide a row-grounded tabular answer because no matching table rows "
                    "were retrieved."
                ),
                abstained=True,
                reason_code="tabular_row_evidence_missing",
                cited_chunk_ids=[],
                used_context_count=0,
                grounding_policy="tabular_row_grounded",
            )

        tabular_chunks = [item for item in context if bool(item.get("is_tabular"))]
        grounded_rows: list[str] = []
        contributing_chunks: list[dict[str, Any]] = []
        for chunk in tabular_chunks:
            matched_rows = chunk.get("matched_rows")
            if not isinstance(matched_rows, list):
                continue
            chunk_contributed = False
            for row in matched_rows:
                if isinstance(row, dict):
                    row_text = str(row.get("row_text", "")).strip()
                else:
                    row_text = str(row).strip()
                if row_text:
                    grounded_rows.append(row_text)
                    chunk_contributed = True
            if chunk_contributed:
                contributing_chunks.append(chunk)

        if not grounded_rows:
            return GenerationResult(
                text=(
                    "I cannot provide a row-grounded tabular answer because no matching table rows "
                    "were retrieved."
                ),
                abstained=True,
                reason_code="tabular_row_evidence_missing",
                cited_chunk_ids=[],
                used_context_count=0,
                grounding_policy="tabular_row_grounded",
            )

        used_chunks = contributing_chunks[:3]
        return GenerationResult(
            text="\n".join(grounded_rows[:3]),
            abstained=False,
            reason_code=None,
            cited_chunk_ids=_unique_chunk_ids(used_chunks),
            used_context_count=len(used_chunks),
            grounding_policy="tabular_row_grounded",
        )

    if not context:
        return GenerationResult(
            text="I cannot answer confidently because no supporting evidence was retrieved.",
            abstained=True,
            reason_code="no_supporting_evidence",
            cited_chunk_ids=[],
            used_context_count=0,
            grounding_policy="extractive_grounded",
        )

    used_chunks = [item for item in context if _has_citable_text(item)][:3]
    if not used_chunks:
        return GenerationResult(
            text="I cannot answer confidently because retrieved evidence had no usable content.",
            abstained=True,
            reason_code="usable_evidence_missing",
            cited_chunk_ids=[],
            used_context_count=0,
            grounding_policy="extractive_grounded",
        )

    summary_lines = [str(item.get("text", "")).strip() for item in used_chunks]
    return GenerationResult(
        text="\n".join(summary_lines),
        abstained=False,
        reason_code=None,
        cited_chunk_ids=_unique_chunk_ids(used_chunks),
        used_context_count=len(used_chunks),
        grounding_policy="extractive_grounded",
    )


def generate_answer(
    query: str,
    context: list[dict[str, Any]],
    *,
    mode: str = "extractive",
    tabular_intent: bool = False,
) -> str:
    return generate_answer_result(
        query,
        context,
        mode=mode,
        tabular_intent=tabular_intent,
    ).text
