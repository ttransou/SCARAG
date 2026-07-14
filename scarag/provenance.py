from __future__ import annotations

from typing import Any

REQUIRED_SOURCE_FIELDS = ("source", "chunk_id")
REQUIRED_CITATION_FIELDS = ("id", "title", "document", "snippet", "score", "chunk_id", "doc_type")


def _missing_fields(record: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for field in required:
        value = record.get(field)
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
    return missing


def validate_source_fields(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = 0
    missing_by_field = {field: 0 for field in REQUIRED_SOURCE_FIELDS}

    for chunk in chunks:
        missing = _missing_fields(chunk, REQUIRED_SOURCE_FIELDS)
        if missing:
            invalid += 1
            for field in missing:
                missing_by_field[field] += 1

    total = len(chunks)
    valid = max(0, total - invalid)
    completeness_rate = 1.0 if total == 0 else valid / total
    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "missing_by_field": missing_by_field,
        "completeness_rate": round(completeness_rate, 4),
    }


def validate_citation_fields(citations: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = 0
    missing_by_field = {field: 0 for field in REQUIRED_CITATION_FIELDS}

    for citation in citations:
        missing = _missing_fields(citation, REQUIRED_CITATION_FIELDS)
        if missing:
            invalid += 1
            for field in missing:
                missing_by_field[field] += 1

    total = len(citations)
    valid = max(0, total - invalid)
    completeness_rate = 1.0 if total == 0 else valid / total
    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "missing_by_field": missing_by_field,
        "completeness_rate": round(completeness_rate, 4),
    }


def validate_provenance(chunks: list[dict[str, Any]], citations: list[dict[str, Any]]) -> dict[str, Any]:
    source_validation = validate_source_fields(chunks)
    citation_validation = validate_citation_fields(citations)
    complete = source_validation["invalid"] == 0 and citation_validation["invalid"] == 0
    return {
        "complete": complete,
        "source_validation": source_validation,
        "citation_validation": citation_validation,
    }
