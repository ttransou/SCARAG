from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.ingestion.loader import load_documents_with_diagnostics
from scarag.pipeline import build_chunk_index, ingest_documents_with_diagnostics


def test_loader_adds_xml_and_legacy_doc_parser_coverage_with_unsupported_diagnostics(tmp_path: Path) -> None:
    (tmp_path / "notes.xml").write_text(
        "<root><title>Release Notes</title><body>XML parser body.</body></root>",
        encoding="utf-8",
    )
    (tmp_path / "legacy.doc").write_bytes(b"Legacy DOC body with controls and policy details")
    (tmp_path / "archive.bin").write_bytes(b"\x01\x02\x03")

    documents, diagnostics = load_documents_with_diagnostics(tmp_path)

    assert any(doc["extraction_method"] == "xml_parser" for doc in documents)
    assert any(doc["extraction_method"] == "doc_legacy_parser" for doc in documents)

    file_records = diagnostics["files"]
    unsupported = next(record for record in file_records if record["source"].endswith("archive.bin"))
    assert unsupported["status"] == "skipped"
    assert unsupported["skip_reason"] == "unsupported_format"


def test_placeholder_doc_type_does_not_bypass_taxonomy_inference(tmp_path: Path) -> None:
    config = RagConfig(lifecycle_state_path=str(tmp_path / "lifecycle-state.json"))
    docs = [
        {
            "source": str(tmp_path / "policy-update.txt"),
            "text": "This is a control update.",
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert chunks
    assert chunks[0]["doc_type"] == "policy"


def test_tabular_heuristics_reduce_false_positive_prose_classification(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        chunk_size=80,
        overlap=0,
        min_chunk_words=1,
    )
    docs = [
        {
            "source": str(tmp_path / "memo.txt"),
            "text": (
                "The review covered reliability, maintainability, and accessibility goals.\n"
                "Recommendations include phased rollout, extra validation, and wider training support.\n"
                "Each proposal keeps context, rationale, and ownership notes in prose form."
            ),
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert chunks
    assert all(chunk["is_tabular"] is False for chunk in chunks)
    assert all(chunk["source_unit_kind"] == "prose" for chunk in chunks)


def test_non_persistent_ingestion_mode_skips_lifecycle_state_writes(tmp_path: Path) -> None:
    lifecycle_path = tmp_path / "lifecycle-state.json"
    config = RagConfig(
        lifecycle_state_path=str(lifecycle_path),
        ingestion_persist_lifecycle_state=False,
    )
    docs = [
        {
            "source": str(tmp_path / "exploratory.txt"),
            "text": "Exploratory run content for ingestion.",
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert chunks
    assert not lifecycle_path.exists()
    assert chunks[0]["status"] == "active"
    assert chunks[0]["ingestion_iso_ts"]


def test_ingestion_diagnostics_contract_reports_per_file_chunk_counts_and_type_summary(tmp_path: Path) -> None:
    (tmp_path / "policy.txt").write_text("policy controls and approvals", encoding="utf-8")
    (tmp_path / "report.xml").write_text("<doc><p>report summary</p></doc>", encoding="utf-8")
    (tmp_path / "metrics.csv").write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")
    (tmp_path / "skip.me").write_text("ignore", encoding="utf-8")

    config = RagConfig(
        data_path=str(tmp_path),
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        ingestion_persist_lifecycle_state=False,
        table_chunk_rows=1,
        table_overlap_rows=0,
    )

    result = ingest_documents_with_diagnostics(tmp_path, config)

    diagnostics = result["diagnostics"]
    assert diagnostics["contract_version"] == "1.0"
    assert diagnostics["summary"]["total_files"] == 4
    assert diagnostics["summary"]["unsupported_files"] == 1
    assert diagnostics["summary"]["total_chunks"] == len(result["chunks"])
    assert isinstance(diagnostics["summary"]["inferred_doc_type_counts"], dict)

    file_records = diagnostics["files"]
    assert all("parser" in record for record in file_records)
    assert all("skip_reason" in record for record in file_records)
    assert all("chunk_count" in record for record in file_records)

    skipped_record = next(record for record in file_records if record["source"].endswith("skip.me"))
    assert skipped_record["status"] == "skipped"
    assert skipped_record["skip_reason"] == "unsupported_format"
    assert skipped_record["chunk_count"] == 0

    loaded_with_chunks = [record for record in file_records if record["status"] == "loaded"]
    assert loaded_with_chunks
    assert all(record["chunk_count"] >= 1 for record in loaded_with_chunks)
    assert any(record["tabular_chunk_count"] >= 1 for record in loaded_with_chunks if record["source"].endswith("metrics.csv"))


def test_loader_skips_internal_lifecycle_artifacts(tmp_path: Path) -> None:
    (tmp_path / "policy.txt").write_text("policy baseline", encoding="utf-8")
    (tmp_path / ".scarag_lifecycle_state.json").write_text("{}", encoding="utf-8")

    documents, diagnostics = load_documents_with_diagnostics(tmp_path)

    assert any(doc["source"].endswith("policy.txt") for doc in documents)
    assert not any(doc["source"].endswith(".scarag_lifecycle_state.json") for doc in documents)

    skipped = next(
        record
        for record in diagnostics["files"]
        if record["source"].endswith(".scarag_lifecycle_state.json")
    )
    assert skipped["status"] == "skipped"
    assert skipped["skip_reason"] == "internal_artifact"
    assert diagnostics["summary"]["internal_skipped_files"] == 1
