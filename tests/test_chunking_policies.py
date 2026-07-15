from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.pipeline import build_chunk_index


def test_prose_chunking_applies_overlap_policy_by_chunk_type(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        chunk_size=20,
        overlap=5,
        min_chunk_words=1,
    )
    docs = [
        {
            "source": str(tmp_path / "notes.txt"),
            "text": " ".join(f"w{index}" for index in range(1, 31)),
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert len(chunks) == 2
    first_words = chunks[0]["text"].split()
    second_words = chunks[1]["text"].split()
    assert len(first_words) == 20
    assert first_words[-5:] == second_words[:5]


def test_tabular_overlap_is_clamped_to_window_minus_one(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        table_chunk_rows=1,
        table_overlap_rows=5,
    )
    docs = [
        {
            "source": str(tmp_path / "table.txt"),
            "text": "1 | alpha\n2 | beta",
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert len(chunks) == 2
    assert all(chunk["tabular_chunk_metadata"]["overlap_rows"] == 0 for chunk in chunks)


def test_cohesion_threshold_splits_low_overlap_sentences(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        chunk_size=50,
        overlap=0,
        min_chunk_words=1,
        cohesion_threshold=0.3,
    )
    docs = [
        {
            "source": str(tmp_path / "cohesion.txt"),
            "text": (
                "alpha policy controls and alpha review cadence. "
                "alpha approvals remain aligned with policy governance. "
                "zebra habitat migration patterns change seasonally."
            ),
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert len(chunks) >= 2
    assert all(chunk["source_unit_kind"] == "prose" for chunk in chunks)
    assert len({chunk["source_unit_local_id"] for chunk in chunks}) >= 2
    assert all(chunk["prose_chunk_metadata"]["cohesion_split_applied"] is True for chunk in chunks)


def test_prose_chunks_do_not_cross_source_unit_boundaries(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        chunk_size=100,
        overlap=0,
        min_chunk_words=1,
        cohesion_threshold=0.4,
    )
    docs = [
        {
            "source": str(tmp_path / "boundaries.txt"),
            "text": "alpha controls are documented. beta controls are reviewed. zebra migrations shift yearly.",
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert len(chunks) >= 2
    boundaries = [chunk["source_unit_boundary"] for chunk in chunks]
    for idx in range(len(boundaries) - 1):
        assert boundaries[idx]["unit_end_word_index"] <= boundaries[idx + 1]["unit_start_word_index"]
    for chunk in chunks:
        assert (
            chunk["prose_chunk_metadata"]["absolute_chunk_end_word_index"]
            <= chunk["source_unit_boundary"]["unit_end_word_index"]
        )
        assert (
            chunk["prose_chunk_metadata"]["absolute_chunk_start_word_index"]
            >= chunk["source_unit_boundary"]["unit_start_word_index"]
        )
