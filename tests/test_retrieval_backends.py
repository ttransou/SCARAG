from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.pipeline import build_chunk_index, retrieve_chunks_with_diagnostics, retrieve_via_interface


def _docs(tmp_path: Path) -> list[dict[str, str]]:
    return [
        {
            "source": str(tmp_path / "policy.md"),
            "text": "policy controls and policy review cadence for approvals",
            "doc_type": "policy",
        },
        {
            "source": str(tmp_path / "guide.md"),
            "text": "developer onboarding and workflow guide",
            "doc_type": "guideline",
        },
    ]


def test_tfidf_backend_returns_ranked_results(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="tfidf",
        min_retrieval_score=0.0,
    )
    chunks = build_chunk_index(_docs(tmp_path), config)

    response = retrieve_via_interface(
        "policy approvals",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert response.ranked_chunks
    assert response.ranked_chunks[0]["source"].endswith("policy.md")
    assert response.diagnostics["retained"] >= 1


def test_hybrid_backend_fuses_lexical_and_tfidf(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="hybrid",
        min_retrieval_score=0.0,
    )
    chunks = build_chunk_index(_docs(tmp_path), config)

    response = retrieve_via_interface(
        "policy review",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert response.ranked_chunks
    assert response.diagnostics["retained"] == len(response.ranked_chunks)


def test_retrieve_chunks_with_diagnostics_respects_backend_selection(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="tfidf",
        min_retrieval_score=0.0,
    )
    chunks = build_chunk_index(_docs(tmp_path), config)

    ranked, diagnostics = retrieve_chunks_with_diagnostics(
        "policy controls",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert ranked
    assert diagnostics["candidates"] >= 1
    assert diagnostics["retained"] >= 1
