from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scarag.config import RagConfig
from scarag.lifecycle import LifecycleStateStore

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def _content_fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _source_unit_id(source: str) -> str:
    normalized = str(Path(source)).replace("\\", "/").lower()
    return f"su_{hashlib.sha1(normalized.encode('utf-8', errors='ignore')).hexdigest()[:16]}"


def _parse_iso_ts(value: str | None) -> tuple[datetime | None, bool]:
    if not value:
        return None, False
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, True
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC), False
    return parsed, False


def _freshness_filter_reason(record: dict[str, Any], config: RagConfig) -> str | None:
    if config.freshness_max_age_days is None:
        return None

    candidate_fields = (
        ["last_upsert_iso_ts", "ingestion_iso_ts"]
        if config.freshness_use_last_upsert_first
        else ["ingestion_iso_ts", "last_upsert_iso_ts"]
    )

    saw_missing = False
    saw_invalid = False
    for field in candidate_fields:
        raw_value = str(record.get(field) or "").strip()
        if not raw_value:
            saw_missing = True
            continue
        selected_ts, invalid = _parse_iso_ts(raw_value)
        if invalid:
            saw_invalid = True
            continue
        if selected_ts is None:
            saw_missing = True
            continue

        age = datetime.now(UTC) - selected_ts
        if age.days > config.freshness_max_age_days:
            return "freshness_stale"
        return None

    if saw_invalid and config.freshness_invalid_ts_policy.strip().lower() == "exclude":
        return "freshness_invalid_timestamp"

    if saw_missing and config.freshness_missing_ts_policy.strip().lower() == "exclude":
        return "freshness_missing_timestamp"

    return None


def _lifecycle_filter_reason(chunk: dict[str, Any], config: RagConfig, store: LifecycleStateStore) -> str | None:
    source_unit_id = str(chunk.get("source_unit_id", "")).strip()
    if not source_unit_id:
        if config.lifecycle_require_persisted_record:
            return "missing_source_unit_id"
        return None

    record_obj = store.get(source_unit_id)
    if record_obj is None:
        if config.lifecycle_require_persisted_record:
            return "missing_persisted_record"
        record = {
            "status": str(chunk.get("status", "")),
            "deletion_mark_iso_ts": chunk.get("deletion_mark_iso_ts"),
            "ingestion_iso_ts": chunk.get("ingestion_iso_ts"),
            "last_upsert_iso_ts": chunk.get("last_upsert_iso_ts"),
        }
    else:
        record = {
            "status": record_obj.status,
            "deletion_mark_iso_ts": record_obj.deletion_mark_iso_ts,
            "ingestion_iso_ts": record_obj.ingestion_iso_ts,
            "last_upsert_iso_ts": record_obj.last_upsert_iso_ts,
        }

    status = str(record.get("status", "")).strip().lower()
    if config.exclude_soft_deleted and (
        status == "soft_deleted" or bool(record.get("deletion_mark_iso_ts"))
    ):
        return "soft_deleted"

    allow_set = {item.strip().lower() for item in config.status_allow_list if item.strip()}
    if allow_set and status not in allow_set:
        return "status_allow_list"

    deny_set = {item.strip().lower() for item in config.status_deny_list if item.strip()}
    if status in deny_set:
        return "status_deny_list"

    freshness_reason = _freshness_filter_reason(record, config)
    if freshness_reason is not None:
        return freshness_reason

    return None


def infer_doc_type(source: str, text: str) -> str:
    source_lower = source.lower()
    text_lower = text.lower()
    doc_type_patterns = {
        "policy": ["policy", "policies"],
        "procedure": ["procedure", "procedures", "sop"],
        "faq": ["faq", "frequently asked"],
        "guideline": ["guideline", "guidelines", "best practice"],
        "report": ["report", "summary", "analysis"],
        "contract": ["contract", "agreement", "terms"],
    }
    for doc_type, patterns in doc_type_patterns.items():
        if any(pattern in source_lower or pattern in text_lower for pattern in patterns):
            return doc_type
    return "unknown"


def _looks_tabular(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for line in lines[:20] if "|" in line)
    comma_lines = sum(1 for line in lines[:20] if line.count(",") >= 2)
    return pipe_lines >= 2 or comma_lines >= 2


def _chunk_prose(text: str, chunk_size: int, overlap: int, min_chunk_words: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    safe_chunk_size = max(chunk_size, 20)
    safe_overlap = max(0, min(overlap, safe_chunk_size - 1))
    step = max(1, safe_chunk_size - safe_overlap)

    chunks: list[str] = []
    for start in range(0, len(words), step):
        candidate = words[start : start + safe_chunk_size]
        if not candidate:
            continue
        if len(candidate) < min_chunk_words and chunks:
            chunks[-1] = f"{chunks[-1]} {' '.join(candidate)}".strip()
            continue
        chunks.append(" ".join(candidate))

    return chunks


def _chunk_tabular(text: str, table_chunk_rows: int, table_overlap_rows: int) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) <= 1:
        return [text.strip()] if text.strip() else []

    header = lines[0]
    rows = lines[1:]
    safe_rows = max(1, table_chunk_rows)
    safe_overlap = max(0, min(table_overlap_rows, safe_rows - 1))
    step = max(1, safe_rows - safe_overlap)

    chunks: list[str] = []
    for start in range(0, len(rows), step):
        window = rows[start : start + safe_rows]
        if not window:
            continue
        chunks.append("\n".join([header, *window]))
    return chunks


def _load_synonyms(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {"terms": {}, "intent_groups": {}}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"terms": {}, "intent_groups": {}}


def expand_query_terms(query: str, thesaurus: dict[str, Any]) -> set[str]:
    terms = _tokenize(query)
    expanded = set(terms)

    synonym_terms = thesaurus.get("terms", {}) if isinstance(thesaurus, dict) else {}
    for term in terms:
        for synonym in synonym_terms.get(term, []):
            expanded.update(_tokenize(str(synonym)))

    # Reverse map: if query contains synonym text, include canonical key.
    for canonical_term, synonym_values in synonym_terms.items():
        canonical_tokens = _tokenize(str(canonical_term))
        synonym_tokens = {_tokenize(str(value))[0] for value in synonym_values if _tokenize(str(value))}
        if any(token in expanded for token in synonym_tokens):
            expanded.update(canonical_tokens)

    return expanded


def is_tabular_intent(query: str, thesaurus: dict[str, Any]) -> bool:
    query_terms = set(_tokenize(query))
    intent_groups = thesaurus.get("intent_groups", {}) if isinstance(thesaurus, dict) else {}
    tabular_terms: set[str] = set()

    for value in intent_groups.get("tabular", []):
        tabular_terms.update(_tokenize(str(value)))

    return bool(query_terms & tabular_terms)


def build_chunk_index(
    documents: list[dict[str, Any]],
    config: RagConfig,
    lifecycle_store: LifecycleStateStore | None = None,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()
    store = lifecycle_store or LifecycleStateStore(config.lifecycle_state_path)

    for document in documents:
        source = str(document.get("source", "unknown"))
        text = str(document.get("text", "")).strip()
        if not text:
            continue

        fingerprint = _content_fingerprint(text)
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)

        source_unit_id = _source_unit_id(source)
        lifecycle_record = store.upsert(
            source_unit_id=source_unit_id,
            source=source,
            content_fingerprint=fingerprint,
        )

        doc_type = str(document.get("doc_type") or infer_doc_type(source, text))
        tabular = _looks_tabular(text)
        raw_chunks = (
            _chunk_tabular(text, config.table_chunk_rows, config.table_overlap_rows)
            if tabular
            else _chunk_prose(text, config.chunk_size, config.overlap, config.min_chunk_words)
        )

        for index, chunk_text in enumerate(raw_chunks):
            normalized = chunk_text.strip()
            if not normalized:
                continue
            chunks.append(
                {
                    "chunk_id": f"{Path(source).name}:{index}",
                    "source_unit_id": source_unit_id,
                    "source": source,
                    "text": normalized,
                    "doc_type": doc_type,
                    "domain_area": "unknown",
                    "is_tabular": tabular,
                    "content_fingerprint": _content_fingerprint(normalized),
                    "ingestion_iso_ts": lifecycle_record.ingestion_iso_ts,
                    "last_upsert_iso_ts": lifecycle_record.last_upsert_iso_ts,
                    "deletion_mark_iso_ts": lifecycle_record.deletion_mark_iso_ts,
                    "status": lifecycle_record.status,
                }
            )

    return chunks


def retrieve_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    config: RagConfig,
    thesaurus: dict[str, Any],
) -> list[dict[str, Any]]:
    ranked, _ = retrieve_chunks_with_diagnostics(query, chunks, config, thesaurus)
    return ranked


def retrieve_chunks_with_diagnostics(
    query: str,
    chunks: list[dict[str, Any]],
    config: RagConfig,
    thesaurus: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    query_terms = expand_query_terms(query, thesaurus)
    if not query_terms:
        return [], {
            "candidates": 0,
            "retained": 0,
            "filtered_soft_deleted": 0,
            "filtered_status_allow_list": 0,
            "filtered_status_deny_list": 0,
            "filtered_freshness_stale": 0,
            "filtered_freshness_missing_timestamp": 0,
            "filtered_freshness_invalid_timestamp": 0,
            "filtered_missing_source_unit_id": 0,
            "filtered_missing_persisted_record": 0,
        }

    lifecycle_store = LifecycleStateStore(config.lifecycle_state_path)
    diagnostics = {
        "candidates": 0,
        "retained": 0,
        "filtered_soft_deleted": 0,
        "filtered_status_allow_list": 0,
        "filtered_status_deny_list": 0,
        "filtered_freshness_stale": 0,
        "filtered_freshness_missing_timestamp": 0,
        "filtered_freshness_invalid_timestamp": 0,
        "filtered_missing_source_unit_id": 0,
        "filtered_missing_persisted_record": 0,
    }
    weighted: list[dict[str, Any]] = []
    for chunk in chunks:
        diagnostics["candidates"] += 1
        filter_reason = _lifecycle_filter_reason(chunk, config, lifecycle_store)
        if filter_reason is not None:
            key = f"filtered_{filter_reason}"
            diagnostics[key] = diagnostics.get(key, 0) + 1
            continue

        text_terms = _tokenize(str(chunk.get("text", "")))
        if not text_terms:
            continue

        overlap_count = sum(1 for token in text_terms if token in query_terms)
        overlap_score = overlap_count / max(1, len(query_terms))

        doc_type = str(chunk.get("doc_type", "unknown")).lower()
        doc_weight = 1.1 if doc_type in {"policy", "procedure", "report", "faq"} else 1.0
        final_score = overlap_score * doc_weight

        if final_score < config.min_retrieval_score:
            continue

        with_score = dict(chunk)
        with_score["score"] = round(final_score, 4)
        weighted.append(with_score)

    weighted.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    retained = weighted[: config.top_k]
    diagnostics["retained"] = len(retained)
    return retained, diagnostics


def load_thesaurus(config: RagConfig) -> dict[str, Any]:
    return _load_synonyms(config.thesaurus_path)
