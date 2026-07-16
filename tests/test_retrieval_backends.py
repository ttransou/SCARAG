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


def test_vector_backend_returns_ranked_results(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="vector",
        min_retrieval_score=0.0,
        vector_dimension=128,
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


def test_vector_backend_uses_fallback_adapter_for_unknown_name(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="vector",
        vector_backend_adapter="unknown_adapter",
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
    assert response.diagnostics["retained"] >= 1


def test_lexical_similarity_metric_jaccard_changes_ranking_behavior(tmp_path: Path) -> None:
    docs = [
        {
            "source": str(tmp_path / "repetitive.md"),
            "text": "alpha alpha alpha alpha alpha",
            "doc_type": "guideline",
        },
        {
            "source": str(tmp_path / "balanced.md"),
            "text": "alpha beta gamma",
            "doc_type": "guideline",
        },
    ]

    overlap_config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-overlap.json"),
        retrieval_backend="lexical",
        lexical_similarity_metric="overlap",
        min_retrieval_score=0.0,
    )
    overlap_chunks = build_chunk_index(docs, overlap_config)
    overlap_response = retrieve_via_interface(
        "alpha beta gamma",
        overlap_chunks,
        overlap_config,
        {"terms": {}, "intent_groups": {}},
    )

    jaccard_config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-jaccard.json"),
        retrieval_backend="lexical",
        lexical_similarity_metric="jaccard",
        min_retrieval_score=0.0,
    )
    jaccard_chunks = build_chunk_index(docs, jaccard_config)
    jaccard_response = retrieve_via_interface(
        "alpha beta gamma",
        jaccard_chunks,
        jaccard_config,
        {"terms": {}, "intent_groups": {}},
    )

    assert overlap_response.ranked_chunks[0]["source"].endswith("repetitive.md")
    assert jaccard_response.ranked_chunks[0]["source"].endswith("balanced.md")


def test_vector_similarity_metric_euclidean_is_supported(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="vector",
        vector_similarity_metric="euclidean",
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


def test_metadata_weight_rules_can_rank_by_source_unit_kind(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        metadata_weight_rules={
            "source_unit_kind": {
                "tabular_section": 1.4,
                "prose": 0.8,
            }
        },
    )
    docs = [
        {
            "source": str(tmp_path / "prose.txt"),
            "text": "alpha discussion note",
            "doc_type": "unknown",
        },
        {
            "source": str(tmp_path / "table.csv"),
            "text": "name | value\nalpha | 1",
            "doc_type": "unknown",
        },
    ]
    chunks = build_chunk_index(docs, config)

    response = retrieve_via_interface(
        "alpha",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert response.ranked_chunks
    assert response.ranked_chunks[0]["source"].endswith("table.csv")
    assert response.ranked_chunks[0]["source_unit_kind"] == "tabular_section"


def test_metadata_weighting_can_be_disabled(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        metadata_weighting_enabled=False,
        metadata_weight_rules={
            "source_unit_kind": {
                "tabular_section": 2.0,
                "prose": 0.5,
            }
        },
    )
    docs = [
        {
            "source": str(tmp_path / "prose.txt"),
            "text": "alpha discussion note",
            "doc_type": "unknown",
        },
        {
            "source": str(tmp_path / "table.csv"),
            "text": "name | value\nalpha | 1",
            "doc_type": "unknown",
        },
    ]
    chunks = build_chunk_index(docs, config)

    response = retrieve_via_interface(
        "alpha",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert response.ranked_chunks
    assert response.ranked_chunks[0]["source"].endswith("prose.txt")


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


def test_retrieval_preserves_chunk_metadata_fields(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
    )
    docs = [
        {
            "source": str(tmp_path / "table.docx"),
            "text": "Name | Value\nAlpha | 1\nName | Value\nBeta | 2",
            "doc_type": "report",
            "table_metadata": [
                {
                    "table_id": "docx_table_0",
                    "row_count": 2,
                    "column_count": 2,
                    "header_fields": ["Name", "Value"],
                }
            ],
            "image_markers": [{"marker_id": "img_0", "content_type": "image"}],
        }
    ]
    chunks = build_chunk_index(docs, config)

    response = retrieve_via_interface(
        "alpha value",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert response.ranked_chunks
    first = response.ranked_chunks[0]
    assert first.get("tabular_chunk_metadata") is not None
    assert first.get("source_unit_local_id")
    assert first.get("source_unit_kind") == "tabular_section"
    assert isinstance(first.get("table_metadata"), list)
    assert isinstance(first.get("image_markers"), list)
    assert isinstance(first.get("boilerplate_signal"), dict)


def test_boilerplate_penalty_demotes_repeated_chunks(tmp_path: Path) -> None:
    common_words = " ".join(f"w{index}" for index in range(1, 19))
    repeated_prefix = f"alpha beta {common_words}"
    docs = [
        {
            "source": str(tmp_path / "a.md"),
            "text": f"{repeated_prefix} taila uniquea",
            "doc_type": "unknown",
        },
        {
            "source": str(tmp_path / "b.md"),
            "text": f"{repeated_prefix} tailb uniqueb",
            "doc_type": "unknown",
        },
        {
            "source": str(tmp_path / "c.md"),
            "text": "alpha beta bespoke guidance",
            "doc_type": "unknown",
        },
    ]

    no_penalty = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-no-penalty.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        chunk_size=20,
        overlap=0,
        min_chunk_words=1,
        boilerplate_penalty_enabled=False,
    )
    no_penalty_chunks = build_chunk_index(docs, no_penalty)
    no_penalty_response = retrieve_via_interface(
        "alpha beta",
        no_penalty_chunks,
        no_penalty,
        {"terms": {}, "intent_groups": {}},
    )

    with_penalty = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-with-penalty.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        chunk_size=20,
        overlap=0,
        min_chunk_words=1,
        boilerplate_penalty_enabled=True,
        boilerplate_penalty_strength=0.9,
        boilerplate_penalty_min_factor=0.2,
    )
    with_penalty_chunks = build_chunk_index(docs, with_penalty)
    with_penalty_response = retrieve_via_interface(
        "alpha beta",
        with_penalty_chunks,
        with_penalty,
        {"terms": {}, "intent_groups": {}},
    )

    assert no_penalty_response.ranked_chunks
    assert with_penalty_response.ranked_chunks
    assert no_penalty_response.ranked_chunks[0]["source"].endswith("a.md")
    assert with_penalty_response.ranked_chunks[0]["source"].endswith("c.md")


def test_table_aware_boost_promotes_tabular_match_on_tabular_intent(tmp_path: Path) -> None:
    docs = [
        {
            "source": str(tmp_path / "prose.txt"),
            "text": "table table table alpha value narrative",
            "doc_type": "unknown",
        },
        {
            "source": str(tmp_path / "table.csv"),
            "text": "name | value\nalpha | 1",
            "doc_type": "unknown",
        },
    ]

    no_boost = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-no-boost.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        table_aware_boost_enabled=False,
    )
    no_boost_chunks = build_chunk_index(docs, no_boost)
    no_boost_response = retrieve_via_interface(
        "table alpha value",
        no_boost_chunks,
        no_boost,
        {"terms": {}, "intent_groups": {"tabular": ["table"]}},
    )

    with_boost = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-with-boost.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        table_aware_boost_enabled=True,
        table_intent_base_boost=1.0,
        table_header_match_boost=1.0,
        table_row_match_boost=1.0,
    )
    with_boost_chunks = build_chunk_index(docs, with_boost)
    with_boost_response = retrieve_via_interface(
        "table alpha value",
        with_boost_chunks,
        with_boost,
        {"terms": {}, "intent_groups": {"tabular": ["table"]}},
    )

    assert no_boost_response.ranked_chunks[0]["source"].endswith("prose.txt")
    assert with_boost_response.ranked_chunks[0]["source"].endswith("table.csv")


def test_verbose_retrieval_diagnostics_include_query_terms_and_rank_explanations(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
        retrieval_diagnostics_mode="verbose",
        retrieval_diagnostics_top_n=2,
    )
    chunks = build_chunk_index(_docs(tmp_path), config)

    ranked, diagnostics = retrieve_chunks_with_diagnostics(
        "policy controls",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert ranked
    assert diagnostics.get("backend") == "lexical"
    assert "policy" in diagnostics.get("query_terms", [])
    explanations = diagnostics.get("final_rank_explanations", [])
    assert isinstance(explanations, list)
    assert explanations
    assert "components" in explanations[0]
