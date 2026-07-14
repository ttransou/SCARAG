from __future__ import annotations

from scarag.provenance import validate_provenance


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
