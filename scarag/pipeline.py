from __future__ import annotations

import math
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scarag.config import RagConfig
from scarag.lifecycle import LifecycleStateStore
from scarag.metadata import EvidenceMetadata, build_confidence_inputs, utc_now_iso
from scarag.retrieval.interfaces import RetrievalRequest, RetrievalResponse, Retriever

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_TABULAR_SPLIT_RE = re.compile(r"\s*\|\s*|\s*,\s*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


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


def _normalize_window_policy(window_size: int, overlap: int, *, min_window_size: int) -> tuple[int, int, int]:
    safe_window_size = max(min_window_size, window_size)
    safe_overlap = max(0, min(overlap, safe_window_size - 1))
    step = max(1, safe_window_size - safe_overlap)
    return safe_window_size, safe_overlap, step


def _token_overlap(left: str, right: str) -> float:
    left_terms = set(_tokenize(left))
    right_terms = set(_tokenize(right))
    if not left_terms or not right_terms:
        return 0.0
    intersection = len(left_terms & right_terms)
    union = len(left_terms | right_terms)
    return 0.0 if union == 0 else intersection / union


def _split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text.strip()) if part.strip()]
    return parts if parts else ([text.strip()] if text.strip() else [])


def _split_prose_source_units(text: str, cohesion_threshold: float) -> list[dict[str, Any]]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if not paragraphs:
        return []

    units: list[dict[str, Any]] = []
    unit_index = 0
    cumulative_word_index = 1

    for paragraph in paragraphs:
        paragraph_units: list[str] = []
        cohesion_applied = False

        if cohesion_threshold > 0:
            sentences = _split_sentences(paragraph)
            if len(sentences) > 1:
                current = [sentences[0]]
                current_context = sentences[0]
                for sentence in sentences[1:]:
                    if _token_overlap(current_context, sentence) < cohesion_threshold:
                        paragraph_units.append(" ".join(current).strip())
                        current = [sentence]
                        current_context = sentence
                        cohesion_applied = True
                        continue

                    current.append(sentence)
                    current_context = f"{current_context} {sentence}".strip()

                if current:
                    paragraph_units.append(" ".join(current).strip())

        if not paragraph_units:
            paragraph_units = [paragraph]

        for unit_text in paragraph_units:
            word_count = len(unit_text.split())
            if word_count == 0:
                continue
            units.append(
                {
                    "source_unit_index": unit_index,
                    "text": unit_text,
                    "unit_start_word_index": cumulative_word_index,
                    "unit_end_word_index": cumulative_word_index + word_count - 1,
                    "unit_word_count": word_count,
                    "cohesion_split_applied": cohesion_applied,
                }
            )
            cumulative_word_index += word_count
            unit_index += 1

    return units


def _split_tabular_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []
    if "|" in stripped or "," in stripped:
        return [cell.strip() for cell in _TABULAR_SPLIT_RE.split(stripped) if cell.strip()]
    return [stripped]


def _normalized_tabular_line(line: str) -> str:
    cells = _split_tabular_cells(line)
    if len(cells) < 2:
        return line.strip().lower()
    return " | ".join(cells).lower()


def _is_likely_header_row(line: str) -> bool:
    cells = _split_tabular_cells(line)
    if len(cells) < 2:
        return False

    alpha_cells = sum(1 for cell in cells if any(char.isalpha() for char in cell))
    numeric_like_cells = sum(
        1
        for cell in cells
        if cell.replace(".", "", 1).isdigit() or cell.replace("-", "", 1).isdigit()
    )
    # Treat rows with numeric-like cells as data rows; inferred headers should be label-only.
    return alpha_cells >= max(1, len(cells) // 2) and numeric_like_cells == 0


def _header_candidates_from_metadata(table_metadata: Any) -> set[str]:
    if not isinstance(table_metadata, list):
        return set()

    candidates: set[str] = set()
    for record in table_metadata:
        if not isinstance(record, dict):
            continue
        fields = record.get("header_fields")
        if not isinstance(fields, list):
            continue
        cleaned = [str(field).strip() for field in fields if str(field).strip()]
        if len(cleaned) < 2:
            continue
        candidates.add(_normalized_tabular_line(" | ".join(cleaned)))
    return candidates


def _tabular_sections(text: str, table_metadata: Any) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    known_headers = _header_candidates_from_metadata(table_metadata)
    if known_headers:
        header_indexes = [
            index
            for index, line in enumerate(lines)
            if _normalized_tabular_line(line) in known_headers
        ]
        if header_indexes:
            sections: list[dict[str, Any]] = []
            normalized_headers = [_normalized_tabular_line(lines[index]) for index in header_indexes]
            header_counts = Counter(normalized_headers)
            seen_headers: Counter[str] = Counter()
            for position, start in enumerate(header_indexes):
                end = header_indexes[position + 1] if position + 1 < len(header_indexes) else len(lines)
                header = lines[start]
                rows = lines[start + 1 : end]
                if rows:
                    normalized_header = _normalized_tabular_line(header)
                    seen_headers[normalized_header] += 1
                    sections.append(
                        {
                            "header": header,
                            "rows": rows,
                            "section_index": position,
                            "header_source": "table_metadata",
                            "header_repeat_index": seen_headers[normalized_header],
                            "header_repeat_count": header_counts[normalized_header],
                            "section_row_count": len(rows),
                        }
                    )
            if sections:
                return sections

    inferred_header: str | None = None
    if len(lines) >= 2 and _is_likely_header_row(lines[0]):
        inferred_header = lines[0]
        rows = lines[1:]
    else:
        rows = lines

    if not rows:
        return []
    return [
        {
            "header": inferred_header,
            "rows": rows,
            "section_index": 0,
            "header_source": "inferred" if inferred_header else "none",
            "header_repeat_index": 1 if inferred_header else 0,
            "header_repeat_count": 1 if inferred_header else 0,
            "section_row_count": len(rows),
        }
    ]


def _chunk_prose_with_metadata(
    text: str,
    chunk_size: int,
    overlap: int,
    min_chunk_words: int,
) -> list[tuple[str, dict[str, int]]]:
    words = text.split()
    if not words:
        return []

    safe_chunk_size, safe_overlap, step = _normalize_window_policy(
        chunk_size,
        overlap,
        min_window_size=20,
    )

    chunks: list[tuple[str, dict[str, int]]] = []
    for start in range(0, len(words), step):
        candidate = words[start : start + safe_chunk_size]
        if not candidate:
            continue
        if len(candidate) < min_chunk_words and chunks:
            existing_text, existing_meta = chunks[-1]
            merged_words = existing_text.split() + candidate
            chunks[-1] = (
                " ".join(merged_words).strip(),
                {
                    "chunk_start_word_index": int(existing_meta.get("chunk_start_word_index", 1)),
                    "chunk_end_word_index": start + len(candidate),
                    "chunk_word_count": len(merged_words),
                    "overlap_words": safe_overlap,
                },
            )
            continue
        chunks.append(
            (
                " ".join(candidate),
                {
                    "chunk_start_word_index": start + 1,
                    "chunk_end_word_index": start + len(candidate),
                    "chunk_word_count": len(candidate),
                    "overlap_words": safe_overlap,
                },
            )
        )

    return chunks


def _chunk_prose(text: str, chunk_size: int, overlap: int, min_chunk_words: int) -> list[str]:
    return [
        chunk_text
        for chunk_text, _chunk_meta in _chunk_prose_with_metadata(text, chunk_size, overlap, min_chunk_words)
    ]


def _chunk_tabular(
    text: str,
    table_chunk_rows: int,
    table_overlap_rows: int,
    table_metadata: Any = None,
) -> list[tuple[str, dict[str, Any]]]:
    sections = _tabular_sections(text, table_metadata)
    if not sections:
        normalized = text.strip()
        if not normalized:
            return []
        return [
            (
                normalized,
                {
                    "section_index": 0,
                    "has_header": False,
                    "header_text": None,
                    "header_source": "none",
                    "header_repeat_index": 0,
                    "header_repeat_count": 0,
                    "row_start_index": 1,
                    "row_end_index": len([line for line in normalized.splitlines() if line.strip()]),
                    "window_row_count": len([line for line in normalized.splitlines() if line.strip()]),
                    "overlap_rows": 0,
                },
            )
        ]

    safe_rows, safe_overlap, step = _normalize_window_policy(
        table_chunk_rows,
        table_overlap_rows,
        min_window_size=1,
    )

    chunks: list[tuple[str, dict[str, Any]]] = []
    for section in sections:
        header = section.get("header")
        rows = list(section.get("rows", []))
        section_index = int(section.get("section_index", 0))
        header_source = str(section.get("header_source", "none"))
        header_repeat_index = int(section.get("header_repeat_index", 0))
        header_repeat_count = int(section.get("header_repeat_count", 0))
        section_row_count = int(section.get("section_row_count", len(rows)))

        for start in range(0, len(rows), step):
            window = rows[start : start + safe_rows]
            if not window:
                continue
            if start > 0 and len(window) <= safe_overlap:
                continue
            if header:
                chunk_text = "\n".join([str(header), *window])
            else:
                chunk_text = "\n".join(window)

            row_start = start + 1
            row_end = start + len(window)
            chunk_meta = {
                "section_index": section_index,
                "has_header": bool(header),
                "header_text": str(header) if header else None,
                "header_source": header_source,
                "header_repeat_index": header_repeat_index,
                "header_repeat_count": header_repeat_count,
                "section_row_count": section_row_count,
                "row_start_index": row_start,
                "row_end_index": row_end,
                "window_row_count": len(window),
                "overlap_rows": safe_overlap,
            }
            chunks.append((chunk_text, chunk_meta))
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

        extraction_method = str(document.get("extraction_method") or "text_file_parser")
        extraction_ts = str(document.get("extraction_ts") or utc_now_iso())

        doc_type = str(document.get("doc_type") or infer_doc_type(source, text))
        table_metadata = document.get("table_metadata")
        image_markers = document.get("image_markers")
        tabular = bool(table_metadata) or _looks_tabular(text)
        if tabular:
            raw_tabular_chunks = _chunk_tabular(
                text,
                config.table_chunk_rows,
                config.table_overlap_rows,
                table_metadata,
            )
            chunk_records = [
                {
                    "text": chunk_text,
                    "tabular_chunk_metadata": chunk_meta,
                    "prose_chunk_metadata": None,
                    "source_unit_kind": "tabular_section",
                    "source_unit_local_id": f"{source_unit_id}:table:{int(chunk_meta.get('section_index', 0))}",
                    "source_unit_boundary": {
                        "unit_start_row_index": 1,
                        "unit_end_row_index": int(chunk_meta.get("section_row_count", 0)),
                    },
                }
                for chunk_text, chunk_meta in raw_tabular_chunks
            ]
        else:
            prose_units = _split_prose_source_units(text, float(config.cohesion_threshold))
            chunk_records = []
            for prose_unit in prose_units:
                unit_text = str(prose_unit.get("text", ""))
                unit_start = int(prose_unit.get("unit_start_word_index", 1))
                unit_end = int(prose_unit.get("unit_end_word_index", unit_start))
                unit_index = int(prose_unit.get("source_unit_index", 0))

                for chunk_text, chunk_meta in _chunk_prose_with_metadata(
                    unit_text,
                    config.chunk_size,
                    config.overlap,
                    config.min_chunk_words,
                ):
                    rel_start = int(chunk_meta.get("chunk_start_word_index", 1))
                    rel_end = int(chunk_meta.get("chunk_end_word_index", rel_start))
                    abs_start = unit_start + rel_start - 1
                    abs_end = unit_start + rel_end - 1
                    chunk_records.append(
                        {
                            "text": chunk_text,
                            "tabular_chunk_metadata": None,
                            "prose_chunk_metadata": {
                                "chunk_start_word_index": rel_start,
                                "chunk_end_word_index": rel_end,
                                "chunk_word_count": int(chunk_meta.get("chunk_word_count", 0)),
                                "overlap_words": int(chunk_meta.get("overlap_words", 0)),
                                "absolute_chunk_start_word_index": abs_start,
                                "absolute_chunk_end_word_index": abs_end,
                                "cohesion_split_applied": bool(prose_unit.get("cohesion_split_applied", False)),
                            },
                            "source_unit_kind": "prose",
                            "source_unit_local_id": f"{source_unit_id}:prose:{unit_index}",
                            "source_unit_boundary": {
                                "unit_start_word_index": unit_start,
                                "unit_end_word_index": unit_end,
                            },
                        }
                    )

        for index, chunk_record in enumerate(chunk_records):
            chunk_text = str(chunk_record.get("text", ""))
            normalized = chunk_text.strip()
            if not normalized:
                continue
            chunk_id = f"{Path(source).name}:{index}"
            confidence_inputs = build_confidence_inputs(
                extraction_method=extraction_method,
                status=lifecycle_record.status,
                deletion_mark_iso_ts=lifecycle_record.deletion_mark_iso_ts,
                is_tabular=tabular,
            )
            metadata = EvidenceMetadata(
                chunk_id=chunk_id,
                source_unit_id=source_unit_id,
                source=source,
                text=normalized,
                doc_type=doc_type,
                domain_area="unknown",
                is_tabular=tabular,
                content_fingerprint=_content_fingerprint(normalized),
                extraction_method=extraction_method,
                extraction_ts=extraction_ts,
                ingestion_iso_ts=lifecycle_record.ingestion_iso_ts,
                last_upsert_iso_ts=lifecycle_record.last_upsert_iso_ts,
                deletion_mark_iso_ts=lifecycle_record.deletion_mark_iso_ts,
                status=lifecycle_record.status,
                confidence_inputs=confidence_inputs,
                tabular_chunk_metadata=chunk_record.get("tabular_chunk_metadata"),
                prose_chunk_metadata=chunk_record.get("prose_chunk_metadata"),
                source_unit_local_id=chunk_record.get("source_unit_local_id"),
                source_unit_kind=chunk_record.get("source_unit_kind"),
                source_unit_boundary=chunk_record.get("source_unit_boundary"),
                table_metadata=table_metadata if isinstance(table_metadata, list) else None,
                image_markers=image_markers if isinstance(image_markers, list) else None,
            )
            chunks.append(metadata.to_dict())

    return chunks


def retrieve_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    config: RagConfig,
    thesaurus: dict[str, Any],
) -> list[dict[str, Any]]:
    response = retrieve_via_interface(query, chunks, config, thesaurus)
    return response.ranked_chunks


def _empty_diagnostics() -> dict[str, int]:
    return {
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


def _apply_lifecycle_filters(
    chunks: list[dict[str, Any]],
    config: RagConfig,
    lifecycle_store: LifecycleStateStore,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    diagnostics = _empty_diagnostics()
    candidates: list[dict[str, Any]] = []

    for chunk in chunks:
        diagnostics["candidates"] += 1
        filter_reason = _lifecycle_filter_reason(chunk, config, lifecycle_store)
        if filter_reason is not None:
            key = f"filtered_{filter_reason}"
            diagnostics[key] = diagnostics.get(key, 0) + 1
            continue
        candidates.append(chunk)

    return candidates, diagnostics


def _score_lexical(
    query_terms: set[str],
    candidates: list[dict[str, Any]],
    config: RagConfig,
) -> list[dict[str, Any]]:
    weighted: list[dict[str, Any]] = []
    if not query_terms:
        return weighted

    for chunk in candidates:
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
    return weighted


def _score_tfidf(
    query_terms: set[str],
    candidates: list[dict[str, Any]],
    config: RagConfig,
) -> list[dict[str, Any]]:
    weighted: list[dict[str, Any]] = []
    if not query_terms or not candidates:
        return weighted

    tokenized_docs = [_tokenize(str(chunk.get("text", ""))) for chunk in candidates]
    doc_term_counts = [Counter(tokens) for tokens in tokenized_docs]
    if not any(doc_term_counts):
        return weighted

    doc_frequency: Counter[str] = Counter()
    for counts in doc_term_counts:
        for term in counts:
            doc_frequency[term] += 1

    doc_count = len(candidates)
    query_count = Counter(query_terms)
    query_weights: dict[str, float] = {}
    for term, count in query_count.items():
        idf = math.log((1 + doc_count) / (1 + doc_frequency.get(term, 0))) + 1.0
        query_weights[term] = float(count) * idf

    query_norm = math.sqrt(sum(value * value for value in query_weights.values()))
    if query_norm == 0.0:
        return weighted

    for chunk, term_counts in zip(candidates, doc_term_counts):
        if not term_counts:
            continue

        total_terms = sum(term_counts.values())
        doc_weights: dict[str, float] = {}
        for term, count in term_counts.items():
            tf = count / max(1, total_terms)
            idf = math.log((1 + doc_count) / (1 + doc_frequency.get(term, 0))) + 1.0
            doc_weights[term] = tf * idf

        dot = sum(doc_weights.get(term, 0.0) * query_weights.get(term, 0.0) for term in query_weights)
        doc_norm = math.sqrt(sum(value * value for value in doc_weights.values()))
        similarity = 0.0 if doc_norm == 0.0 else dot / (doc_norm * query_norm)

        doc_type = str(chunk.get("doc_type", "unknown")).lower()
        doc_weight = 1.1 if doc_type in {"policy", "procedure", "report", "faq"} else 1.0
        final_score = similarity * doc_weight

        if final_score < config.min_retrieval_score:
            continue

        with_score = dict(chunk)
        with_score["score"] = round(final_score, 4)
        weighted.append(with_score)

    weighted.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return weighted


def _rrf_fuse(
    lexical: list[dict[str, Any]],
    tfidf: list[dict[str, Any]],
    config: RagConfig,
) -> list[dict[str, Any]]:
    rank_lex = {str(item.get("chunk_id", "")): idx for idx, item in enumerate(lexical, start=1)}
    rank_tfidf = {str(item.get("chunk_id", "")): idx for idx, item in enumerate(tfidf, start=1)}
    all_ids = set(rank_lex) | set(rank_tfidf)

    by_id: dict[str, dict[str, Any]] = {}
    for item in lexical + tfidf:
        key = str(item.get("chunk_id", ""))
        if key and key not in by_id:
            by_id[key] = item

    fused: list[dict[str, Any]] = []
    for key in all_ids:
        lex_rank = rank_lex.get(key)
        tfidf_rank = rank_tfidf.get(key)
        lex_rrf = 0.0 if lex_rank is None else 1.0 / (config.hybrid_rrf_k + lex_rank)
        tfidf_rrf = 0.0 if tfidf_rank is None else 1.0 / (config.hybrid_rrf_k + tfidf_rank)
        score = lex_rrf + tfidf_rrf

        item = dict(by_id[key])
        item["score"] = round(score, 6)
        fused.append(item)

    fused.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return fused


def retrieve_chunks_with_diagnostics(
    query: str,
    chunks: list[dict[str, Any]],
    config: RagConfig,
    thesaurus: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    response = retrieve_via_interface(query, chunks, config, thesaurus)
    return response.ranked_chunks, response.diagnostics


class LexicalRetriever(Retriever):
    """Default retrieval backend used by the current public baseline."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        if not query_terms:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        ranked = _score_lexical(query_terms, candidates, request.config)
        retained = ranked[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        return RetrievalResponse(ranked_chunks=retained, diagnostics=diagnostics)


class TfidfRetriever(Retriever):
    """TF-IDF cosine similarity backend for retrieval."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        if not query_terms:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        ranked = _score_tfidf(query_terms, candidates, request.config)
        retained = ranked[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        return RetrievalResponse(ranked_chunks=retained, diagnostics=diagnostics)


class HybridRrfRetriever(Retriever):
    """Hybrid retriever that fuses lexical and TF-IDF ranking using RRF."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        if not query_terms:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        lexical = _score_lexical(query_terms, candidates, request.config)
        tfidf = _score_tfidf(query_terms, candidates, request.config)
        fused = _rrf_fuse(lexical, tfidf, request.config)
        retained = fused[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        return RetrievalResponse(ranked_chunks=retained, diagnostics=diagnostics)


def retrieve_via_interface(
    query: str,
    chunks: list[dict[str, Any]],
    config: RagConfig,
    thesaurus: dict[str, Any],
    retriever: Retriever | None = None,
) -> RetrievalResponse:
    if retriever is None:
        backend = config.retrieval_backend.strip().lower()
        if backend == "tfidf":
            active_retriever: Retriever = TfidfRetriever()
        elif backend in {"hybrid", "hybrid_rrf"}:
            active_retriever = HybridRrfRetriever()
        else:
            active_retriever = LexicalRetriever()
    else:
        active_retriever = retriever

    request = RetrievalRequest(
        query=query,
        chunks=chunks,
        config=config,
        thesaurus=thesaurus,
    )
    return active_retriever.retrieve(request)


def load_thesaurus(config: RagConfig) -> dict[str, Any]:
    return _load_synonyms(config.thesaurus_path)
