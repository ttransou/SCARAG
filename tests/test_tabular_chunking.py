from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.pipeline import build_chunk_index


def test_tabular_chunking_preserves_first_row_when_no_header(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        table_chunk_rows=1,
        table_overlap_rows=0,
    )
    docs = [
        {
            "source": str(tmp_path / "table.txt"),
            "text": "1001 | alpha | open\n1002 | beta | closed",
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)

    assert len(chunks) == 2
    assert chunks[0]["is_tabular"] is True
    assert chunks[0]["text"] == "1001 | alpha | open"
    assert chunks[1]["text"] == "1002 | beta | closed"
    assert chunks[0]["tabular_chunk_metadata"]["has_header"] is False
    assert chunks[0]["tabular_chunk_metadata"]["row_start_index"] == 1
    assert chunks[1]["tabular_chunk_metadata"]["row_start_index"] == 2


def test_tabular_chunking_uses_table_metadata_headers_for_sectioning(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        table_chunk_rows=1,
        table_overlap_rows=0,
    )
    docs = [
        {
            "source": str(tmp_path / "report.docx"),
            "text": "release notes\nName | Value\nAlpha | 1\nName | Value\nBeta | 2",
            "doc_type": "unknown",
            "table_metadata": [
                {
                    "table_id": "docx_table_0",
                    "row_count": 2,
                    "column_count": 2,
                    "header_fields": ["Name", "Value"],
                }
            ],
        }
    ]

    chunks = build_chunk_index(docs, config)
    chunk_texts = [chunk["text"] for chunk in chunks]
    chunk_meta = [chunk["tabular_chunk_metadata"] for chunk in chunks]

    assert len(chunks) == 2
    assert all(text.startswith("Name | Value\n") for text in chunk_texts)
    assert all("release notes" not in text for text in chunk_texts)
    assert any("Alpha | 1" in text for text in chunk_texts)
    assert any("Beta | 2" in text for text in chunk_texts)
    assert {meta["header_repeat_index"] for meta in chunk_meta} == {1, 2}
    assert all(meta["header_repeat_count"] == 2 for meta in chunk_meta)
    assert all(meta["header_source"] == "table_metadata" for meta in chunk_meta)


def test_tabular_chunking_row_overlap_without_header(tmp_path: Path) -> None:
    config = RagConfig(
        lifecycle_state_path=str(tmp_path / "lifecycle-state.json"),
        table_chunk_rows=2,
        table_overlap_rows=1,
    )
    docs = [
        {
            "source": str(tmp_path / "status.txt"),
            "text": "1001 | alpha | open\n1002 | beta | closed\n1003 | gamma | pending",
            "doc_type": "unknown",
        }
    ]

    chunks = build_chunk_index(docs, config)
    chunk_texts = [chunk["text"] for chunk in chunks]

    assert len(chunks) == 2
    assert chunk_texts[0] == "1001 | alpha | open\n1002 | beta | closed"
    assert chunk_texts[1] == "1002 | beta | closed\n1003 | gamma | pending"
