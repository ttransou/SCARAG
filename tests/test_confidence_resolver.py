from __future__ import annotations

from datetime import UTC, datetime

from scarag.confidence import resolve_confidence


def test_resolver_abstains_when_no_evidence() -> None:
    result = resolve_confidence("policy", [])
    assert result.label == "abstain"
    assert result.reason == "no_evidence"


def test_resolver_returns_high_for_strong_structured_active_evidence() -> None:
    chunks = [
        {
            "score": 0.95,
            "is_tabular": True,
            "confidence_inputs": {
                "base_extraction_tier": "structured_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": True,
            },
        },
        {
            "score": 0.88,
            "is_tabular": True,
            "confidence_inputs": {
                "base_extraction_tier": "structured_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": True,
            },
        },
    ]
    result = resolve_confidence("policy", chunks)
    assert result.label == "high"


def test_resolver_abstains_for_tabular_intent_without_tabular_evidence() -> None:
    chunks = [
        {
            "score": 0.91,
            "is_tabular": False,
            "confidence_inputs": {
                "base_extraction_tier": "document_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": False,
            },
        }
    ]
    result = resolve_confidence("show totals by quarter", chunks, tabular_intent=True)
    assert result.label == "abstain"
    assert result.reason == "tabular_evidence_missing"


def test_resolver_returns_low_for_mixed_quality_evidence() -> None:
    chunks = [
        {
            "score": 0.48,
            "is_tabular": False,
            "confidence_inputs": {
                "base_extraction_tier": "plain_text_parse",
                "lifecycle_status": "pending_review",
                "has_deletion_mark": False,
                "tabular_evidence": False,
            },
        },
        {
            "score": 0.46,
            "is_tabular": False,
            "confidence_inputs": {
                "base_extraction_tier": "plain_text_parse",
                "lifecycle_status": "retired",
                "has_deletion_mark": False,
                "tabular_evidence": False,
            },
        },
    ]
    result = resolve_confidence("policy", chunks)
    assert result.label in {"low", "abstain"}


def test_temporal_decay_reduces_confidence_for_stale_evidence() -> None:
    chunks = [
        {
            "score": 0.95,
            "is_tabular": False,
            "last_upsert_iso_ts": "2020-01-01T00:00:00Z",
            "confidence_inputs": {
                "base_extraction_tier": "structured_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": False,
            },
        }
    ]

    without_decay = resolve_confidence(
        "policy",
        chunks,
        temporal_decay_enabled=False,
    )
    with_decay = resolve_confidence(
        "policy",
        chunks,
        temporal_decay_enabled=True,
        temporal_decay_half_life_days=30.0,
        temporal_decay_floor=0.2,
        now_provider=lambda: datetime(2030, 1, 1, tzinfo=UTC),
    )

    assert without_decay.label == "high"
    assert with_decay.score < without_decay.score
    assert with_decay.label in {"low", "abstain"}


def test_temporal_decay_keeps_recent_evidence_high_confidence() -> None:
    chunks = [
        {
            "score": 0.95,
            "is_tabular": False,
            "last_upsert_iso_ts": "2030-01-01T00:00:00Z",
            "confidence_inputs": {
                "base_extraction_tier": "structured_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": False,
            },
        }
    ]

    with_decay = resolve_confidence(
        "policy",
        chunks,
        temporal_decay_enabled=True,
        temporal_decay_half_life_days=180.0,
        temporal_decay_floor=0.35,
        now_provider=lambda: datetime(2030, 1, 2, tzinfo=UTC),
    )

    assert with_decay.label == "high"


def test_intent_alignment_boosts_score_for_matching_tabular_intent() -> None:
    chunks = [
        {
            "score": 0.72,
            "is_tabular": True,
            "tabular_grounded": True,
            "doc_type": "report",
            "confidence_inputs": {
                "base_extraction_tier": "document_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": True,
            },
        }
    ]
    thesaurus = {"intent_groups": {"tabular": ["table", "row", "column"]}}

    baseline = resolve_confidence(
        "show row totals",
        chunks,
        tabular_intent=True,
        thesaurus=thesaurus,
        intent_adjustment_enabled=False,
    )
    with_intent = resolve_confidence(
        "show row totals",
        chunks,
        tabular_intent=True,
        thesaurus=thesaurus,
        intent_adjustment_enabled=True,
        intent_match_boost=0.2,
        intent_mismatch_penalty=0.25,
        intent_adjustment_floor=0.7,
    )

    assert with_intent.score > baseline.score


def test_intent_alignment_penalizes_score_for_intent_mismatch() -> None:
    chunks = [
        {
            "score": 0.92,
            "is_tabular": False,
            "doc_type": "policy",
            "confidence_inputs": {
                "base_extraction_tier": "structured_parse",
                "lifecycle_status": "active",
                "has_deletion_mark": False,
                "tabular_evidence": False,
            },
        }
    ]
    thesaurus = {"intent_groups": {"tabular": ["table", "rows"]}}

    baseline = resolve_confidence(
        "table rows",
        chunks,
        tabular_intent=False,
        thesaurus=thesaurus,
        intent_adjustment_enabled=False,
    )
    with_intent = resolve_confidence(
        "table rows",
        chunks,
        tabular_intent=False,
        thesaurus=thesaurus,
        intent_adjustment_enabled=True,
        intent_match_boost=0.1,
        intent_mismatch_penalty=0.35,
        intent_adjustment_floor=0.6,
    )

    assert with_intent.score < baseline.score
