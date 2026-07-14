from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.metadata import CANONICAL_EVIDENCE_FIELDS, missing_canonical_fields
from scarag.pipeline import build_chunk_index, retrieve_via_interface


def test_chunk_records_match_canonical_evidence_schema(tmp_path: Path) -> None:
    config = RagConfig(lifecycle_state_path=str(tmp_path / "lifecycle-state.json"))
    docs = [
        {
            "source": str(tmp_path / "policy.txt"),
            "text": "policy review cadence and escalation paths",
            "doc_type": "policy",
            "extraction_method": "text_file_parser",
            "extraction_ts": "2026-01-01T00:00:00Z",
        }
    ]

    chunks = build_chunk_index(docs, config)
    assert chunks

    for chunk in chunks:
        assert set(CANONICAL_EVIDENCE_FIELDS).issubset(set(chunk))
        assert missing_canonical_fields(chunk) == []


def test_retrieval_interface_returns_ranked_chunks_and_diagnostics(tmp_path: Path) -> None:
    config = RagConfig(lifecycle_state_path=str(tmp_path / "lifecycle-state.json"))
    docs = [
        {
            "source": str(tmp_path / "policy.md"),
            "text": "policy approvals and review controls",
            "doc_type": "policy",
            "extraction_method": "text_file_parser",
            "extraction_ts": "2026-01-01T00:00:00Z",
        }
    ]
    chunks = build_chunk_index(docs, config)

    response = retrieve_via_interface(
        "policy approvals",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )

    assert response.ranked_chunks
    assert response.diagnostics["candidates"] >= 1
    assert response.diagnostics["retained"] >= 1
