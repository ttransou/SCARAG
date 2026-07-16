from __future__ import annotations

from scarag.provenance import (
    filter_complete_citations,
    filter_complete_source_chunks,
    validate_citation_quality,
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
    assert report["citation_quality"]["invalid"] == 0


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


def test_validate_citation_quality_flags_short_untraceable_and_duplicate_citations() -> None:
    source_chunks = [
        {"source": "data/policy.md", "chunk_id": "policy:0", "text": "policy body"},
        {"source": "data/guide.md", "chunk_id": "guide:0", "text": "guide body"},
    ]
    citations = [
        {
            "id": "policy:0",
            "title": "policy",
            "document": "data/policy.md",
            "snippet": "policy text is long enough to keep",
            "score": 0.9,
            "chunk_id": "policy:0",
            "doc_type": "policy",
        },
        {
            "id": "guide:0",
            "title": "guide",
            "document": "data/wrong-guide.md",
            "snippet": "guide text is long enough to keep",
            "score": 0.7,
            "chunk_id": "guide:0",
            "doc_type": "guide",
        },
        {
            "id": "policy:0-dup",
            "title": "policy",
            "document": "data/policy.md",
            "snippet": "policy text is long enough to keep",
            "score": 0.6,
            "chunk_id": "policy:0",
            "doc_type": "policy",
        },
        {
            "id": "tiny:0",
            "title": "tiny",
            "document": "data/guide.md",
            "snippet": "too short",
            "score": 0.5,
            "chunk_id": "guide:0",
            "doc_type": "guide",
        },
    ]

    report = validate_citation_quality(citations, source_chunks)
    assert report["total"] == 4
    assert report["valid"] == 1
    assert report["invalid"] == 3
    assert report["dropped_by_reason"]["source_traceability"] == 1
    assert report["dropped_by_reason"]["duplicate_policy"] == 1
    assert report["dropped_by_reason"]["snippet_adequacy"] == 1


def test_filter_complete_citations_applies_quality_checks() -> None:
    source_chunks = [{"source": "data/policy.md", "chunk_id": "policy:0", "text": "policy text"}]
    citations = [
        {
            "id": "policy:0",
            "title": "policy",
            "document": "data/policy.md",
            "snippet": "policy text is long enough to keep",
            "score": 0.9,
            "chunk_id": "policy:0",
            "doc_type": "policy",
        },
        {
            "id": "policy:0-dup",
            "title": "policy",
            "document": "data/policy.md",
            "snippet": "policy text is long enough to keep",
            "score": 0.8,
            "chunk_id": "policy:0",
            "doc_type": "policy",
        },
        {
            "id": "policy:1",
            "title": "policy",
            "document": "data/policy.md",
            "snippet": "short",
            "score": 0.4,
            "chunk_id": "policy:1",
            "doc_type": "policy",
        },
    ]

    retained, report = filter_complete_citations(citations, source_chunks)
    assert [citation["id"] for citation in retained] == ["policy:0"]
    assert report["retained"] == 1
    assert report["quality"]["dropped_by_reason"]["duplicate_policy"] == 1
    assert report["quality"]["dropped_by_reason"]["snippet_adequacy"] == 1
