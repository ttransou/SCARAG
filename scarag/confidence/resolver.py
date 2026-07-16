from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any, Callable

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


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


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(str(text))}


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


def _parse_iso_ts(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _temporal_decay_factor(
    chunks: list[dict[str, Any]],
    *,
    half_life_days: float,
    floor: float,
    now_provider: Callable[[], datetime] | None = None,
) -> float:
    if not chunks:
        return 1.0

    safe_half_life = max(1e-6, float(half_life_days))
    safe_floor = max(0.0, min(1.0, float(floor)))
    now = now_provider() if now_provider is not None else datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    factors: list[float] = []
    for chunk in chunks[:5]:
        timestamp = _parse_iso_ts(chunk.get("last_upsert_iso_ts"))
        if timestamp is None:
            timestamp = _parse_iso_ts(chunk.get("ingestion_iso_ts"))
        if timestamp is None:
            factors.append(1.0)
            continue

        age_days = max(0.0, (now - timestamp).total_seconds() / 86400.0)
        raw_factor = 0.5 ** (age_days / safe_half_life)
        factors.append(max(safe_floor, min(1.0, raw_factor)))

    if not factors:
        return 1.0
    return sum(factors) / len(factors)


def _infer_intents(query: str, thesaurus: dict[str, Any] | None, tabular_intent: bool) -> set[str]:
    detected: set[str] = set()
    if tabular_intent:
        detected.add("tabular")

    if not isinstance(thesaurus, dict):
        return detected

    groups = thesaurus.get("intent_groups")
    if not isinstance(groups, dict):
        return detected

    query_terms = _tokenize(query)
    if not query_terms:
        return detected

    for group_name, values in groups.items():
        name = str(group_name).strip().lower()
        if not name:
            continue
        terms: set[str] = set()
        if isinstance(values, list):
            for value in values:
                terms.update(_tokenize(str(value)))
        if terms & query_terms:
            detected.add(name)

    return detected


def _chunk_supports_intent(chunk: dict[str, Any], intent_name: str) -> bool:
    normalized_intent = str(intent_name).strip().lower()
    if normalized_intent == "tabular":
        if bool(chunk.get("is_tabular")) or bool(chunk.get("tabular_grounded")):
            return True
        inputs = chunk.get("confidence_inputs")
        if isinstance(inputs, dict) and bool(inputs.get("tabular_evidence")):
            return True
        return False

    doc_type = str(chunk.get("doc_type", "")).strip().lower()
    return bool(doc_type) and doc_type == normalized_intent


def _intent_alignment_factor(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    tabular_intent: bool,
    thesaurus: dict[str, Any] | None,
    match_boost: float,
    mismatch_penalty: float,
    floor: float,
) -> float:
    intents = _infer_intents(query, thesaurus, tabular_intent)
    if not intents:
        return 1.0

    matches = 0
    mismatches = 0
    for intent in sorted(intents):
        supports = any(_chunk_supports_intent(chunk, intent) for chunk in chunks[:5])
        if supports:
            matches += 1
        else:
            mismatches += 1

    total = max(1, matches + mismatches)
    matched_ratio = matches / total
    mismatch_ratio = mismatches / total
    safe_floor = max(0.0, min(1.0, float(floor)))

    factor = 1.0
    if matches > 0:
        factor *= 1.0 + max(0.0, float(match_boost)) * matched_ratio
    if mismatches > 0:
        penalty_factor = 1.0 - max(0.0, float(mismatch_penalty)) * mismatch_ratio
        factor *= max(safe_floor, penalty_factor)
    return max(safe_floor, min(1.5, factor))


def resolve_confidence(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    tabular_intent: bool = False,
    thesaurus: dict[str, Any] | None = None,
    high_threshold: float = 0.72,
    low_threshold: float = 0.45,
    temporal_decay_enabled: bool = True,
    temporal_decay_half_life_days: float = 365.0,
    temporal_decay_floor: float = 0.35,
    intent_adjustment_enabled: bool = True,
    intent_match_boost: float = 0.1,
    intent_mismatch_penalty: float = 0.25,
    intent_adjustment_floor: float = 0.7,
    now_provider: Callable[[], datetime] | None = None,
) -> ConfidenceResult:
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

    if temporal_decay_enabled:
        decay_factor = _temporal_decay_factor(
            chunks,
            half_life_days=temporal_decay_half_life_days,
            floor=temporal_decay_floor,
            now_provider=now_provider,
        )
        score *= decay_factor

    if intent_adjustment_enabled:
        intent_factor = _intent_alignment_factor(
            query,
            chunks,
            tabular_intent=tabular_intent,
            thesaurus=thesaurus,
            match_boost=intent_match_boost,
            mismatch_penalty=intent_mismatch_penalty,
            floor=intent_adjustment_floor,
        )
        score *= intent_factor

    score = max(0.0, min(1.0, score))

    if score >= high_threshold:
        return ConfidenceResult(label="high", score=score, reason="strong_grounded_evidence")
    if score >= low_threshold:
        return ConfidenceResult(label="low", score=score, reason="limited_or_mixed_evidence")
    return ConfidenceResult(label="abstain", score=score, reason="insufficient_evidence_quality")
