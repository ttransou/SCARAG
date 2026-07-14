from __future__ import annotations

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
