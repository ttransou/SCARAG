from __future__ import annotations

import json
from pathlib import Path

from scripts.fallbacks import FALLBACK_ENV, select_fallback


def _write_fallback_fixture(path: Path) -> None:
    entries = [
        {
            "id": "faq_override",
            "question_examples": ["faq-only override marker"],
            "response": "Use the deployment FAQ guidance.",
            "type": "resource",
        },
        {
            "id": "intent_match",
            "question_examples": ["how to deploy service"],
            "response": "Use the deployment runbook in docs/deploy.md.",
            "type": "resource",
            "confidence_threshold": 0.4,
        },
        {
            "id": "generic_fallback",
            "question_examples": [""],
            "response": "I don't have a confident answer right now.",
            "type": "suggest",
        },
    ]
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_fallback_priority_prefers_explicit_faq_mapping(monkeypatch, tmp_path: Path) -> None:
    fixture_path = tmp_path / "fallbacks.json"
    _write_fallback_fixture(fixture_path)
    monkeypatch.setenv(FALLBACK_ENV, str(fixture_path))

    response = select_fallback(
        "how to deploy service",
        retrieval_confidence=0.95,
        faq_map={"how to deploy service": "faq_override"},
    )

    assert response == "Use the deployment FAQ guidance."


def test_fallback_priority_uses_intent_match_before_generic(monkeypatch, tmp_path: Path) -> None:
    fixture_path = tmp_path / "fallbacks.json"
    _write_fallback_fixture(fixture_path)
    monkeypatch.setenv(FALLBACK_ENV, str(fixture_path))

    response = select_fallback("how to deploy service", retrieval_confidence=0.3)

    assert response == "Use the deployment runbook in docs/deploy.md."


def test_fallback_priority_returns_generic_when_intent_threshold_not_met(monkeypatch, tmp_path: Path) -> None:
    fixture_path = tmp_path / "fallbacks.json"
    _write_fallback_fixture(fixture_path)
    monkeypatch.setenv(FALLBACK_ENV, str(fixture_path))

    response = select_fallback("how to deploy service", retrieval_confidence=0.9)

    assert response == "I don't have a confident answer right now."
