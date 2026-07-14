from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConfidenceResult:
    label: str
    score: float
    reason: str


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _retrieval_strength(chunks: list[dict[str, Any]]) -> float:
    if not chunks:
        return 0.0
    top_scores = sorted((_safe_float(chunk.get("score")) for chunk in chunks), reverse=True)[:3]
    if not top_scores:
        return 0.0
    return max(0.0, min(1.0, sum(top_scores) / len(top_scores)))


def _extraction_signal(chunks: list[dict[str, Any]]) -> float:
    if not chunks:
        return 0.0

    tier_weights = {
        "structured_parse": 1.0,
        "document_parse": 0.8,
        "plain_text_parse": 0.65,
    }

    values: list[float] = []
    for chunk in chunks[:5]:
        inputs = chunk.get("confidence_inputs")
        if not isinstance(inputs, dict):
            values.append(0.6)
            continue
        tier = str(inputs.get("base_extraction_tier", "plain_text_parse")).strip().lower()
        values.append(tier_weights.get(tier, 0.6))

    return sum(values) / max(1, len(values))


def _lifecycle_signal(chunks: list[dict[str, Any]]) -> float:
    if not chunks:
        return 0.0

    scores: list[float] = []
    for chunk in chunks[:5]:
        inputs = chunk.get("confidence_inputs")
        status = ""
        has_deletion_mark = False
        if isinstance(inputs, dict):
            status = str(inputs.get("lifecycle_status", "")).strip().lower()
            has_deletion_mark = bool(inputs.get("has_deletion_mark"))

        if has_deletion_mark or status == "soft_deleted":
            scores.append(0.0)
        elif status in {"active", ""}:
            scores.append(1.0)
        elif status in {"pending_review", "retired"}:
            scores.append(0.5)
        else:
            scores.append(0.7)

    return sum(scores) / max(1, len(scores))


def resolve_confidence(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    tabular_intent: bool = False,
    high_threshold: float = 0.72,
    low_threshold: float = 0.45,
) -> ConfidenceResult:
    del query  # Reserved for future intent-based confidence tuning.

    if not chunks:
        return ConfidenceResult(label="abstain", score=0.0, reason="no_evidence")

    has_tabular_evidence = any(bool(chunk.get("is_tabular")) for chunk in chunks)
    if tabular_intent and not has_tabular_evidence:
        return ConfidenceResult(label="abstain", score=0.0, reason="tabular_evidence_missing")

    retrieval = _retrieval_strength(chunks)
    extraction = _extraction_signal(chunks)
    lifecycle = _lifecycle_signal(chunks)
    evidence_coverage = min(1.0, len(chunks) / 3.0)

    score = (
        retrieval * 0.45
        + extraction * 0.25
        + lifecycle * 0.20
        + evidence_coverage * 0.10
    )
    score = max(0.0, min(1.0, score))

    if score >= high_threshold:
        return ConfidenceResult(label="high", score=score, reason="strong_grounded_evidence")
    if score >= low_threshold:
        return ConfidenceResult(label="low", score=score, reason="limited_or_mixed_evidence")
    return ConfidenceResult(label="abstain", score=score, reason="insufficient_evidence_quality")
