from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any

REQUIRED_SOURCE_FIELDS = ("source", "chunk_id")
REQUIRED_CITATION_FIELDS = ("id", "title", "document", "snippet", "score", "chunk_id", "doc_type")
_MIN_SNIPPET_CHARS = 10
_MIN_SNIPPET_TOKENS = 2
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _token_count(value: Any) -> int:
    return len(_TOKEN_RE.findall(str(value or "")))


def _build_trace_index(chunks: Iterable[dict[str, Any]]) -> dict[str, str]:
    trace_index: dict[str, str] = {}
    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id", "")).strip()
        source = str(chunk.get("source", "")).strip()
        if chunk_id and source and chunk_id not in trace_index:
            trace_index[chunk_id] = source
    return trace_index


def _citation_quality_failures(
    citation: dict[str, Any],
    *,
    trace_index: dict[str, str],
) -> list[str]:
    failures: list[str] = []

    snippet = str(citation.get("snippet", "")).strip()
    if len(snippet) < _MIN_SNIPPET_CHARS or _token_count(snippet) < _MIN_SNIPPET_TOKENS:
        failures.append("snippet_adequacy")

    chunk_id = str(citation.get("chunk_id", "")).strip()
    document = str(citation.get("document", "")).strip()
    if trace_index:
        expected_document = trace_index.get(chunk_id)
        if not expected_document or expected_document != document:
            failures.append("source_traceability")

    return failures


def _empty_quality_report() -> dict[str, Any]:
    return {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "dropped_by_reason": {
            "snippet_adequacy": 0,
            "source_traceability": 0,
            "duplicate_policy": 0,
        },
        "duplicate_groups": 0,
        "quality_rate": 1.0,
    }


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


def validate_citation_quality(
    citations: list[dict[str, Any]],
    source_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    report = _empty_quality_report()
    report["total"] = len(citations)
    trace_index = _build_trace_index(source_chunks)
    seen_keys: set[tuple[str, str]] = set()

    for citation in citations:
        duplicate_key = (
            str(citation.get("chunk_id", "")).strip(),
            _normalize_text(citation.get("document")),
        )
        failures = _citation_quality_failures(citation, trace_index=trace_index)
        if duplicate_key in seen_keys:
            failures.append("duplicate_policy")
        elif duplicate_key[0] and duplicate_key[1]:
            seen_keys.add(duplicate_key)

        if failures:
            report["invalid"] += 1
            if "duplicate_policy" in failures:
                report["duplicate_groups"] += 1
            for failure in failures:
                report["dropped_by_reason"][failure] += 1
        else:
            report["valid"] += 1

    total = report["total"]
    report["quality_rate"] = 1.0 if total == 0 else round(report["valid"] / total, 4)
    return report


def filter_complete_source_chunks(chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    retained: list[dict[str, Any]] = []
    dropped = 0
    missing_by_field = {field: 0 for field in REQUIRED_SOURCE_FIELDS}

    for chunk in chunks:
        missing = _missing_fields(chunk, REQUIRED_SOURCE_FIELDS)
        if missing:
            dropped += 1
            for field in missing:
                missing_by_field[field] += 1
            continue
        retained.append(chunk)

    return retained, {
        "input_total": len(chunks),
        "retained": len(retained),
        "dropped": dropped,
        "missing_by_field": missing_by_field,
    }


def filter_complete_citations(
    citations: list[dict[str, Any]],
    source_chunks: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    retained: list[dict[str, Any]] = []
    dropped = 0
    missing_by_field = {field: 0 for field in REQUIRED_CITATION_FIELDS}

    for citation in citations:
        missing = _missing_fields(citation, REQUIRED_CITATION_FIELDS)
        if missing:
            dropped += 1
            for field in missing:
                missing_by_field[field] += 1
            continue
        retained.append(citation)

    quality_report = validate_citation_quality(retained, source_chunks or [])
    quality_retained: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    trace_index = _build_trace_index(source_chunks or [])

    for citation in retained:
        duplicate_key = (
            str(citation.get("chunk_id", "")).strip(),
            _normalize_text(citation.get("document")),
        )
        failures = _citation_quality_failures(citation, trace_index=trace_index)
        is_duplicate = duplicate_key in seen_keys
        if is_duplicate:
            failures.append("duplicate_policy")
        elif duplicate_key[0] and duplicate_key[1]:
            seen_keys.add(duplicate_key)

        if failures:
            continue
        quality_retained.append(citation)

    return quality_retained, {
        "input_total": len(citations),
        "retained": len(quality_retained),
        "dropped": dropped + quality_report["invalid"],
        "missing_by_field": missing_by_field,
        "quality": quality_report,
    }


def validate_provenance(chunks: list[dict[str, Any]], citations: list[dict[str, Any]]) -> dict[str, Any]:
    source_validation = validate_source_fields(chunks)
    citation_validation = validate_citation_fields(citations)
    citation_quality = validate_citation_quality(citations, chunks)
    complete = (
        source_validation["invalid"] == 0
        and citation_validation["invalid"] == 0
        and citation_quality["invalid"] == 0
    )
    return {
        "complete": complete,
        "source_validation": source_validation,
        "citation_validation": citation_validation,
        "citation_quality": citation_quality,
    }
