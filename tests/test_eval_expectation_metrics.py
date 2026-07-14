from __future__ import annotations

from scripts.run_eval import (
    _confidence_matches,
    _excluded_sources_respected,
    _tabular_terms_matched,
)


def test_confidence_matches_expectation() -> None:
    present, matched = _confidence_matches({"expected_confidence": "high"}, "high")
    assert present is True
    assert matched is True


def test_excluded_sources_respected_detects_violations() -> None:
    retrieved = [{"source": "data/retired_policy.md"}]
    present, compliant = _excluded_sources_respected(retrieved, {"excluded_sources": ["retired"]})
    assert present is True
    assert compliant is False


def test_tabular_terms_matched_detects_expected_terms() -> None:
    grounded_chunks = [{"matched_terms": ["alpha", "q1"]}]
    present, matched = _tabular_terms_matched(grounded_chunks, {"expected_tabular_terms": ["alpha"]})
    assert present is True
    assert matched is True
