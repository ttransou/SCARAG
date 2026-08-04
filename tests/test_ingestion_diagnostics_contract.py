from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.pipeline import ingest_documents_with_diagnostics


def test_ingestion_diagnostics_contract_includes_parser_skip_reason_and_chunk_counts(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "play.xml").write_text(
        "<play><title>Hamlet</title><line>To be</line></play>",
        encoding="utf-8",
    )
    (data_dir / "notes.txt").write_text("policy guidance and review controls", encoding="utf-8")
    (data_dir / "audio.mp3").write_bytes(b"ID3")

    config = RagConfig(
        data_path=str(data_dir),
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        ingestion_persist_lifecycle_state=False,
    )

    result = ingest_documents_with_diagnostics(data_dir, config)
    chunks = result["chunks"]
    diagnostics = result["diagnostics"]

    assert chunks
    assert "files" in diagnostics
    assert "summary" in diagnostics
    assert diagnostics["summary"]["total_chunks"] == len(chunks)
    assert isinstance(diagnostics["summary"]["inferred_doc_type_counts"], dict)

    by_source = {entry["source"]: entry for entry in diagnostics["files"]}
    xml_entry = by_source[str(data_dir / "play.xml")]
    txt_entry = by_source[str(data_dir / "notes.txt")]
    mp3_entry = by_source[str(data_dir / "audio.mp3")]

    assert xml_entry["parser"] == "xml_parser"
    assert xml_entry["status"] == "loaded"
    assert xml_entry["chunk_count"] >= 1

    assert txt_entry["parser"] == "text_file_parser"
    assert txt_entry["status"] == "loaded"
    assert txt_entry["chunk_count"] >= 1

    assert mp3_entry["status"] == "skipped"
    assert mp3_entry["skip_reason"] == "unsupported_format"
    assert mp3_entry["chunk_count"] == 0
