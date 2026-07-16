from __future__ import annotations

from scarag.provenance import (
    filter_complete_citations,
    filter_complete_source_chunks,
    validate_provenance,
)


def test_validate_provenance_complete_when_required_fields_exist() -> None:
    chunks = [
        {
            "source": "data/policy.md",
            "chunk_id": "policy.md:0",
            "doc_type": "policy",
            "text": "policy text",
        }
    ]
    citations = [
        {
            "id": "policy.md:0",
            "title": "policy.md",
            "document": "data/policy.md",
            "snippet": "policy text",
            "score": 0.9,
            "chunk_id": "policy.md:0",
            "doc_type": "policy",
        }
    ]

    report = validate_provenance(chunks, citations)
    assert report["complete"] is True
    assert report["source_validation"]["invalid"] == 0
    assert report["citation_validation"]["invalid"] == 0


def test_validate_provenance_flags_missing_citation_and_source_fields() -> None:
    chunks = [{"source": "", "chunk_id": ""}]
    citations = [
        {
            "id": "",
            "title": "",
            "document": "",
            "snippet": "",
            "score": 0.2,
            "chunk_id": "",
            "doc_type": "",
        }
    ]

    report = validate_provenance(chunks, citations)
    assert report["complete"] is False
    assert report["source_validation"]["invalid"] == 1
    assert report["citation_validation"]["invalid"] == 1
    assert report["citation_validation"]["missing_by_field"]["document"] == 1


def test_filter_complete_source_chunks_drops_records_missing_required_fields() -> None:
    chunks = [
        {"source": "data/policy.md", "chunk_id": "policy:0", "text": "policy"},
        {"source": "", "chunk_id": "policy:1", "text": "invalid source"},
        {"source": "data/policy.md", "chunk_id": "", "text": "invalid chunk id"},
    ]

    retained, report = filter_complete_source_chunks(chunks)
    assert len(retained) == 1
    assert report["dropped"] == 2
    assert report["missing_by_field"]["source"] == 1
    assert report["missing_by_field"]["chunk_id"] == 1


def test_filter_complete_citations_drops_records_missing_required_fields() -> None:
    citations = [
        {
            "id": "policy:0",
            "title": "policy",
            "document": "data/policy.md",
            "snippet": "policy text",
            "score": 0.9,
            "chunk_id": "policy:0",
            "doc_type": "policy",
        },
        {
            "id": "policy:1",
            "title": "",
            "document": "",
            "snippet": "",
            "score": 0.2,
            "chunk_id": "",
            "doc_type": "",
        },
    ]

    retained, report = filter_complete_citations(citations)
    assert len(retained) == 1
    assert report["dropped"] == 1
    assert report["missing_by_field"]["title"] == 1
    assert report["missing_by_field"]["document"] == 1
