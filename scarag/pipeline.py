from __future__ import annotations

import math
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scarag.config import RagConfig
from scarag.ingestion.loader import load_documents_with_diagnostics
from scarag.lifecycle import LifecycleRecord, LifecycleStateStore
from scarag.metadata import EvidenceMetadata, build_confidence_inputs, utc_now_iso
from scarag.retrieval.interfaces import RetrievalRequest, RetrievalResponse, Retriever
from scarag.retrieval.vector_backend import HashingVectorEmbedder, VectorEmbedder, cosine_similarity

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_TABULAR_SPLIT_RE = re.compile(r"\s*\|\s*|\s*,\s*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_DEFAULT_DOC_TYPE_PATTERNS: dict[str, list[str]] = {
    "policy": ["policy", "policies"],
    "procedure": ["procedure", "procedures", "sop"],
    "faq": ["faq", "frequently asked"],
    "guideline": ["guideline", "guidelines", "best practice"],
    "report": ["report", "summary", "analysis"],
    "contract": ["contract", "agreement", "terms"],
}

_DOC_TYPE_PLACEHOLDERS = {
    "unknown",
    "placeholder",
    "tbd",
    "todo",
    "none",
    "null",
    "n/a",
    "na",
    "-",
}

_SOURCE_WORK_MARKER_TOKENS = {
    "pdf",
    "txt",
    "doc",
    "docx",
    "xml",
    "html",
    "mhtml",
    "csv",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "folger",
    "folgershakespeare",
    "ln",
}

_QUERY_SOURCE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "does",
    "evidence",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "there",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def _content_fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _boilerplate_signal_key(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", str(text).strip().lower())
    return _content_fingerprint(collapsed)


def _source_unit_id(source: str) -> str:
    normalized = str(Path(source)).replace("\\", "/").lower()
    return f"su_{hashlib.sha1(normalized.encode('utf-8', errors='ignore')).hexdigest()[:16]}"


def _source_work_metadata(source: str) -> tuple[str, str, list[str], str]:
    path = Path(source)
    source_format = path.suffix.lower().lstrip(".")
    raw_tokens = [token for token in re.split(r"[^a-z0-9]+", path.stem.lower()) if token]

    work_tokens: list[str] = []
    for token in raw_tokens:
        if token in _SOURCE_WORK_MARKER_TOKENS:
            break
        work_tokens.append(token)

    if not work_tokens:
        work_tokens = raw_tokens[:]
    if not work_tokens:
        work_tokens = ["unknown"]

    work_key = "_".join(work_tokens)
    work_title = " ".join(token.capitalize() for token in work_tokens)
    return work_key, work_title, work_tokens, source_format


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


def infer_doc_type(source: str, text: str, taxonomy: dict[str, Any] | None = None) -> str:
    source_lower = source.lower()
    text_lower = text.lower()

    safe_taxonomy = taxonomy if isinstance(taxonomy, dict) else {}

    source_overrides = safe_taxonomy.get("source_overrides")
    if isinstance(source_overrides, list):
        for override in source_overrides:
            if not isinstance(override, dict):
                continue
            doc_type = str(override.get("doc_type", "")).strip().lower()
            contains_terms = override.get("contains")
            if not doc_type or not isinstance(contains_terms, list):
                continue
            normalized_terms = [str(term).strip().lower() for term in contains_terms if str(term).strip()]
            if normalized_terms and any(term in source_lower for term in normalized_terms):
                return doc_type

    extension_defaults = safe_taxonomy.get("extension_defaults")
    if isinstance(extension_defaults, dict):
        source_path = Path(source_lower)
        suffixes = list(source_path.suffixes)
        for suffix in reversed(suffixes):
            mapped_doc_type = extension_defaults.get(suffix)
            if isinstance(mapped_doc_type, str) and mapped_doc_type.strip():
                return mapped_doc_type.strip().lower()

    doc_type_patterns: dict[str, list[str]] = dict(_DEFAULT_DOC_TYPE_PATTERNS)
    taxonomy_doc_types = safe_taxonomy.get("doc_types")
    if isinstance(taxonomy_doc_types, dict):
        for raw_doc_type, definition in taxonomy_doc_types.items():
            doc_type = str(raw_doc_type).strip().lower()
            if not doc_type or not isinstance(definition, dict):
                continue
            patterns = definition.get("patterns")
            if not isinstance(patterns, list):
                continue
            normalized_patterns = [str(pattern).strip().lower() for pattern in patterns if str(pattern).strip()]
            if normalized_patterns:
                doc_type_patterns[doc_type] = normalized_patterns

    for doc_type, patterns in doc_type_patterns.items():
        if any(pattern in source_lower or pattern in text_lower for pattern in patterns):
            return doc_type

    fallback_doc_type = safe_taxonomy.get("default_doc_type")
    if isinstance(fallback_doc_type, str) and fallback_doc_type.strip():
        return fallback_doc_type.strip().lower()
    return "unknown"


def _resolved_doc_type(explicit_doc_type: Any, source: str, text: str, taxonomy: dict[str, Any]) -> str:
    normalized = str(explicit_doc_type or "").strip().lower()
    if normalized and normalized not in _DOC_TYPE_PLACEHOLDERS:
        return normalized
    return infer_doc_type(source, text, taxonomy=taxonomy)


def _legacy_doc_text_is_low_fidelity(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return True

    alpha_chars = sum(1 for char in normalized if char.isalpha())
    alpha_ratio = alpha_chars / max(1, len(normalized))
    noisy_markers = ("bjbj", " BT ", " DT ", "HYPERLINK", "w:WordDocument")
    marker_hits = sum(1 for marker in noisy_markers if marker in normalized)
    normalized_lower = normalized.lower()
    looks_binary_prefixed = normalized_lower.startswith("0 bjbj") or normalized_lower.startswith("bjbj")
    return alpha_ratio < 0.6 or marker_hits >= 2 or looks_binary_prefixed


def _resolved_doc_type_for_document(
    explicit_doc_type: Any,
    source: str,
    text: str,
    taxonomy: dict[str, Any],
    extraction_method: str,
) -> str:
    normalized_method = str(extraction_method).strip().lower()
    if normalized_method.startswith("doc_legacy") and _legacy_doc_text_is_low_fidelity(text):
        # On low-fidelity legacy DOC text, trust source-path and taxonomy defaults over noisy content body.
        return _resolved_doc_type(explicit_doc_type, source, "", taxonomy)
    return _resolved_doc_type(explicit_doc_type, source, text, taxonomy)


def _load_doc_type_taxonomy(config: RagConfig) -> dict[str, Any]:
    metadata = config.metadata if isinstance(config.metadata, dict) else {}
    taxonomy_overlay = metadata.get("taxonomy")
    if not isinstance(taxonomy_overlay, dict):
        return {}

    taxonomy_path = taxonomy_overlay.get("doc_type_taxonomy_path")
    if not isinstance(taxonomy_path, str) or not taxonomy_path.strip():
        return {}

    file_path = Path(taxonomy_path.strip())
    if not file_path.exists():
        return {}

    try:
        loaded = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return loaded if isinstance(loaded, dict) else {}


def _is_tabular_delimiter_profile(lines: list[str], delimiter: str) -> bool:
    row_profiles: list[tuple[int, int]] = []
    row_cells: list[list[str]] = []
    sentence_like_rows = 0
    for line in lines:
        if delimiter not in line:
            continue
        cells = [cell.strip() for cell in line.split(delimiter)]
        non_empty = [cell for cell in cells if cell]
        if len(non_empty) < 2:
            continue
        max_cell_words = max(len(cell.split()) for cell in non_empty)
        row_profiles.append((len(non_empty), max_cell_words))
        row_cells.append(non_empty)
        stripped = line.strip()
        if stripped.endswith((".", "!", "?")):
            sentence_like_rows += 1

    if not row_profiles:
        return False

    min_rows = 2 if delimiter == "|" else 3
    if len(row_profiles) < min_rows:
        return False

    column_counts = [profile[0] for profile in row_profiles]
    max_words_per_cell = [profile[1] for profile in row_profiles]
    dominant_col_count, dominant_col_freq = Counter(column_counts).most_common(1)[0]
    consistent_columns = dominant_col_freq / len(row_profiles)
    concise_cells = sum(1 for count in max_words_per_cell if count <= 8) / len(max_words_per_cell)

    if dominant_col_count < 2:
        return False

    if delimiter == ",":
        if dominant_col_count < 3:
            numeric_second_cells = sum(
                1
                for cells in row_cells
                if len(cells) >= 2 and re.fullmatch(r"[-+]?\d+(\.\d+)?", cells[1].strip())
            )
            short_first_cells = sum(1 for cells in row_cells if len(cells[0].split()) <= 3)
            if numeric_second_cells / len(row_cells) < 0.5:
                return False
            if short_first_cells / len(row_cells) < 0.5:
                return False

    if consistent_columns < 0.6:
        return False
    if concise_cells < 0.6:
        return False
    if sentence_like_rows / len(row_profiles) > 0.4:
        return False
    return True


def _looks_tabular(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()][:30]
    if len(lines) < 2:
        return False
    if _is_tabular_delimiter_profile(lines, "|"):
        return True
    return _is_tabular_delimiter_profile(lines, ",")


def _document_metadata_payload(
    table_metadata: Any,
    image_markers: Any,
    *,
    include_details: bool,
) -> dict[str, Any] | None:
    tables = table_metadata if isinstance(table_metadata, list) else []
    markers = image_markers if isinstance(image_markers, list) else []
    if not tables and not markers:
        return None

    payload: dict[str, Any] = {
        "table_count": len(tables),
        "image_marker_count": len(markers),
        "table_ids": [
            str(item.get("table_id", "")).strip()
            for item in tables
            if isinstance(item, dict) and str(item.get("table_id", "")).strip()
        ],
        "image_marker_ids": [
            str(item.get("marker_id", "")).strip()
            for item in markers
            if isinstance(item, dict) and str(item.get("marker_id", "")).strip()
        ],
    }
    if include_details:
        payload["tables"] = tables
        payload["image_markers"] = markers
    return payload


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


def _tabular_sections_from_explicit_ranges(text: str, table_metadata: Any) -> list[dict[str, Any]]:
    if not isinstance(table_metadata, list):
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    explicit_sections: list[dict[str, Any]] = []
    for record in table_metadata:
        if not isinstance(record, dict):
            continue

        try:
            line_start_index = int(record.get("line_start_index", 0))
            line_end_index = int(record.get("line_end_index", 0))
        except (TypeError, ValueError):
            continue

        if line_start_index <= 0 or line_end_index < line_start_index:
            continue

        section_lines = lines[line_start_index - 1 : line_end_index]
        if not section_lines:
            continue

        has_header = bool(record.get("has_header"))
        header_fields = record.get("header_fields")
        cleaned_header_fields = (
            [str(field).strip() for field in header_fields if str(field).strip()]
            if isinstance(header_fields, list)
            else []
        )

        header: str | None = None
        rows = section_lines
        header_source = "none"
        if has_header and len(section_lines) >= 2:
            header = section_lines[0]
            rows = section_lines[1:]
            header_source = "table_metadata" if cleaned_header_fields else "explicit_range"
        elif not has_header:
            header = None
            rows = section_lines

        if not rows:
            continue

        explicit_sections.append(
            {
                "header": header,
                "rows": rows,
                "section_index": len(explicit_sections),
                "header_source": header_source,
                "header_repeat_index": 1,
                "header_repeat_count": 1,
                "section_row_count": len(rows),
                "table_id": str(record.get("table_id", "")).strip() or None,
                "sheet_name": str(record.get("sheet_name", "")).strip() or None,
                "line_start_index": line_start_index,
                "line_end_index": line_end_index,
                "data_row_start_index": int(record.get("data_row_start_index", 2 if has_header else 1)),
                "data_row_end_index": int(record.get("data_row_end_index", len(section_lines))),
            }
        )

    return explicit_sections


def _tabular_sections(text: str, table_metadata: Any) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    explicit_sections = _tabular_sections_from_explicit_ranges(text, table_metadata)
    if explicit_sections:
        return explicit_sections

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
        table_id = section.get("table_id")
        sheet_name = section.get("sheet_name")
        section_line_start = int(section.get("line_start_index", 1))
        section_line_end = int(
            section.get("line_end_index", section_line_start + len(rows) + (1 if header else 0) - 1)
        )
        data_row_start_index = int(section.get("data_row_start_index", 2 if header else 1))
        data_row_end_index = int(section.get("data_row_end_index", len(rows)))

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
                "table_id": table_id,
                "sheet_name": sheet_name,
                "has_header": bool(header),
                "header_text": str(header) if header else None,
                "header_source": header_source,
                "header_repeat_index": header_repeat_index,
                "header_repeat_count": header_repeat_count,
                "section_row_count": section_row_count,
                "section_line_start_index": section_line_start,
                "section_line_end_index": section_line_end,
                "section_data_row_start_index": data_row_start_index,
                "section_data_row_end_index": data_row_end_index,
                "row_start_index": row_start,
                "row_end_index": row_end,
                "absolute_row_start_index": section_line_start + (1 if header else 0) + row_start - 1,
                "absolute_row_end_index": section_line_start + (1 if header else 0) + row_end - 1,
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
    doc_type_taxonomy = _load_doc_type_taxonomy(config)
    persist_lifecycle_state = bool(config.ingestion_persist_lifecycle_state)
    store = lifecycle_store or LifecycleStateStore(
        config.lifecycle_state_path,
        audit_log_path=config.lifecycle_audit_log_path,
        audit_logging_enabled=config.lifecycle_audit_logging_enabled,
    )

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
        source_work_key, source_work_title, source_work_tokens, source_format = _source_work_metadata(source)
        if persist_lifecycle_state:
            lifecycle_record, lifecycle_action = store.upsert_with_policy(
                source_unit_id=source_unit_id,
                source=source,
                content_fingerprint=fingerprint,
                skip_unchanged=config.lifecycle_skip_unchanged,
            )
            if lifecycle_action == "unchanged_skipped":
                continue
        else:
            now_iso = utc_now_iso()
            lifecycle_record = LifecycleRecord(
                source_unit_id=source_unit_id,
                source=source,
                content_fingerprint=fingerprint,
                ingestion_iso_ts=now_iso,
                last_upsert_iso_ts=now_iso,
                deletion_mark_iso_ts=None,
                status="active",
            )

        extraction_method = str(document.get("extraction_method") or "text_file_parser")
        extraction_ts = str(document.get("extraction_ts") or utc_now_iso())

        doc_type = _resolved_doc_type_for_document(
            document.get("doc_type"),
            source,
            text,
            doc_type_taxonomy,
            extraction_method,
        )
        table_metadata = document.get("table_metadata")
        image_markers = document.get("image_markers")
        document_metadata = _document_metadata_payload(
            table_metadata,
            image_markers,
            include_details=bool(config.chunk_include_document_level_details),
        )
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
                    "source_unit_local_id": (
                        f"{source_unit_id}:table:{chunk_meta['table_id']}"
                        if chunk_meta.get("table_id")
                        else f"{source_unit_id}:table:{int(chunk_meta.get('section_index', 0))}"
                    ),
                    "source_unit_boundary": {
                        "unit_start_row_index": int(chunk_meta.get("section_data_row_start_index", 1)),
                        "unit_end_row_index": int(
                            chunk_meta.get(
                                "section_data_row_end_index",
                                chunk_meta.get("section_row_count", 0),
                            )
                        ),
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
                document_metadata=document_metadata,
                source_work_key=source_work_key,
                source_work_title=source_work_title,
                source_work_tokens=source_work_tokens,
                source_format=source_format,
            )
            chunks.append(metadata.to_dict())

    if chunks:
        frequency: Counter[str] = Counter(
            _boilerplate_signal_key(str(chunk.get("text", ""))) for chunk in chunks
        )
        for chunk in chunks:
            key = _boilerplate_signal_key(str(chunk.get("text", "")))
            repeat_count = int(frequency.get(key, 1))
            chunk["boilerplate_signal"] = {
                "repeat_count": repeat_count,
                "is_repeated": repeat_count > 1,
            }

    return chunks


def ingest_documents_with_diagnostics(
    data_path: str | Path,
    config: RagConfig,
    lifecycle_store: LifecycleStateStore | None = None,
) -> dict[str, Any]:
    documents, loader_diagnostics = load_documents_with_diagnostics(data_path)
    chunks = build_chunk_index(documents, config, lifecycle_store=lifecycle_store)

    chunk_counts_by_source: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "chunk_count": 0,
            "tabular_chunk_count": 0,
            "prose_chunk_count": 0,
            "inferred_doc_types": set(),
        }
    )
    inferred_doc_type_counts: Counter[str] = Counter()
    for chunk in chunks:
        source = str(chunk.get("source", ""))
        if not source:
            continue
        per_source = chunk_counts_by_source[source]
        per_source["chunk_count"] += 1
        if bool(chunk.get("is_tabular")):
            per_source["tabular_chunk_count"] += 1
        else:
            per_source["prose_chunk_count"] += 1
        doc_type = str(chunk.get("doc_type", "unknown")).strip().lower() or "unknown"
        per_source["inferred_doc_types"].add(doc_type)
        inferred_doc_type_counts[doc_type] += 1

    files_with_chunk_stats: list[dict[str, Any]] = []
    diagnostics_files = loader_diagnostics.get("files", []) if isinstance(loader_diagnostics, dict) else []
    for file_record in diagnostics_files if isinstance(diagnostics_files, list) else []:
        if not isinstance(file_record, dict):
            continue
        source = str(file_record.get("source", ""))
        chunk_stats = chunk_counts_by_source.get(
            source,
            {
                "chunk_count": 0,
                "tabular_chunk_count": 0,
                "prose_chunk_count": 0,
                "inferred_doc_types": set(),
            },
        )
        files_with_chunk_stats.append(
            {
                "source": source,
                "parser": file_record.get("parser"),
                "status": file_record.get("status"),
                "skip_reason": file_record.get("skip_reason"),
                "chunk_count": int(chunk_stats.get("chunk_count", 0)),
                "tabular_chunk_count": int(chunk_stats.get("tabular_chunk_count", 0)),
                "prose_chunk_count": int(chunk_stats.get("prose_chunk_count", 0)),
                "inferred_doc_types": sorted(chunk_stats.get("inferred_doc_types", set())),
            }
        )

    summary = loader_diagnostics.get("summary", {}) if isinstance(loader_diagnostics, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    summary["total_chunks"] = len(chunks)
    summary["total_tabular_chunks"] = sum(item["tabular_chunk_count"] for item in files_with_chunk_stats)
    summary["total_prose_chunks"] = sum(item["prose_chunk_count"] for item in files_with_chunk_stats)
    summary["inferred_doc_type_counts"] = dict(sorted(inferred_doc_type_counts.items()))

    diagnostics = {
        "contract_version": "1.0",
        "files": files_with_chunk_stats,
        "summary": summary,
    }
    return {
        "documents": documents,
        "chunks": chunks,
        "diagnostics": diagnostics,
    }


def retrieve_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    config: RagConfig,
    thesaurus: dict[str, Any],
) -> list[dict[str, Any]]:
    response = retrieve_via_interface(query, chunks, config, thesaurus)
    return response.ranked_chunks


def _empty_diagnostics() -> dict[str, Any]:
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
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
    *,
    tabular_intent: bool,
) -> list[dict[str, Any]]:
    weighted: list[dict[str, Any]] = []
    if not query_terms:
        return weighted

    for chunk in candidates:
        text_terms = _tokenize(str(chunk.get("text", "")))
        if not text_terms:
            continue

        overlap_score = _lexical_similarity(query_terms, text_terms, config.lexical_similarity_metric)

        metadata_weight = _metadata_weight(chunk, config)
        boilerplate_penalty = _boilerplate_penalty_factor(chunk, config)
        table_boost = _table_boost_factor(
            query_terms,
            chunk,
            tabular_intent=tabular_intent,
            config=config,
        )
        source_work_boost = _source_work_boost_factor(query_terms, chunk)
        final_score = overlap_score * metadata_weight * boilerplate_penalty * table_boost * source_work_boost

        if final_score < config.min_retrieval_score:
            continue

        with_score = dict(chunk)
        with_score["score"] = round(final_score, 4)
        with_score["score_components"] = _rank_score_components(
            base_similarity=overlap_score,
            metadata_weight=metadata_weight,
            boilerplate_penalty=boilerplate_penalty,
            table_boost=table_boost,
            source_work_boost=source_work_boost,
            final_score=final_score,
        )
        weighted.append(with_score)

    weighted.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return weighted


def _lexical_similarity(query_terms: set[str], text_terms: list[str], metric: str) -> float:
    if not query_terms or not text_terms:
        return 0.0

    normalized_metric = metric.strip().lower()
    text_set = set(text_terms)
    intersection = len(query_terms & text_set)

    if normalized_metric == "jaccard":
        union_size = len(query_terms | text_set)
        return 0.0 if union_size == 0 else intersection / union_size

    if normalized_metric == "containment":
        return intersection / max(1, len(query_terms))

    # Default overlap rewards repeated token matches, preserving baseline behavior.
    overlap_count = sum(1 for token in text_terms if token in query_terms)
    return overlap_count / max(1, len(query_terms))


def _metadata_weight(chunk: dict[str, Any], config: RagConfig) -> float:
    if not config.metadata_weighting_enabled:
        return 1.0

    rules = config.metadata_weight_rules if isinstance(config.metadata_weight_rules, dict) else {}
    if not rules:
        return 1.0

    weight = 1.0
    for field_name, mapping in rules.items():
        if not isinstance(mapping, dict):
            continue

        raw_value = chunk.get(field_name)
        if isinstance(raw_value, bool):
            key = str(raw_value).lower()
        elif raw_value is None:
            key = "__missing__"
        else:
            key = str(raw_value).strip().lower()

        candidate = mapping.get(key)
        if candidate is None:
            continue
        try:
            numeric = float(candidate)
        except (TypeError, ValueError):
            continue
        if numeric <= 0:
            continue
        weight *= numeric

    return weight


def _boilerplate_penalty_factor(chunk: dict[str, Any], config: RagConfig) -> float:
    if not config.boilerplate_penalty_enabled:
        return 1.0

    signal = chunk.get("boilerplate_signal")
    if not isinstance(signal, dict):
        return 1.0

    repeat_count = int(signal.get("repeat_count", 1))
    if repeat_count <= 1:
        return 1.0

    strength = max(0.0, float(config.boilerplate_penalty_strength))
    raw_factor = 1.0 / (1.0 + strength * float(repeat_count - 1))
    floor = max(0.05, min(1.0, float(config.boilerplate_penalty_min_factor)))
    return max(floor, raw_factor)


def _table_boost_factor(
    query_terms: set[str],
    chunk: dict[str, Any],
    *,
    tabular_intent: bool,
    config: RagConfig,
) -> float:
    if not config.table_aware_boost_enabled or not tabular_intent:
        return 1.0

    if not bool(chunk.get("is_tabular")):
        return 1.0

    boost = 1.0 + max(0.0, float(config.table_intent_base_boost))

    header_text = ""
    tabular_meta = chunk.get("tabular_chunk_metadata")
    if isinstance(tabular_meta, dict):
        header_text = str(tabular_meta.get("header_text", "") or "")
    header_terms = set(_tokenize(header_text)) if header_text else set()
    if header_terms and (header_terms & query_terms):
        boost += max(0.0, float(config.table_header_match_boost))

    row_lines = [line.strip() for line in str(chunk.get("text", "")).splitlines() if line.strip()]
    if header_text and row_lines:
        row_lines = row_lines[1:]
    row_matches = 0
    for row in row_lines:
        if set(_tokenize(row)) & query_terms:
            row_matches += 1
    if row_matches > 0:
        boost += max(0.0, float(config.table_row_match_boost))

    return boost


def _source_work_boost_factor(query_terms: set[str], chunk: dict[str, Any]) -> float:
    if not query_terms:
        return 1.0

    focus_terms = {
        term
        for term in query_terms
        if len(term) > 2 and term not in _QUERY_SOURCE_STOPWORDS
    }
    if not focus_terms:
        return 1.0

    raw_chunk_tokens = chunk.get("source_work_tokens")
    if isinstance(raw_chunk_tokens, list):
        chunk_work_tokens = {str(token).strip().lower() for token in raw_chunk_tokens if str(token).strip()}
    else:
        chunk_work_tokens = {
            token.strip().lower()
            for token in str(chunk.get("source_work_key", "")).split("_")
            if token.strip()
        }
    if not chunk_work_tokens:
        return 1.0

    overlap = focus_terms & chunk_work_tokens
    if not overlap:
        return 1.0

    work_match_ratio = len(overlap) / len(chunk_work_tokens)
    query_match_ratio = len(overlap) / len(focus_terms)
    boost_strength = (0.4 * work_match_ratio) + (0.2 * query_match_ratio)
    return 1.0 + min(0.5, boost_strength)


def _rank_score_components(
    *,
    base_similarity: float,
    metadata_weight: float,
    boilerplate_penalty: float,
    table_boost: float,
    source_work_boost: float,
    final_score: float,
) -> dict[str, float]:
    return {
        "base_similarity": round(base_similarity, 6),
        "metadata_weight": round(metadata_weight, 6),
        "boilerplate_penalty": round(boilerplate_penalty, 6),
        "table_boost": round(table_boost, 6),
        "source_work_boost": round(source_work_boost, 6),
        "final_score": round(final_score, 6),
    }


def _attach_retrieval_diagnostics(
    diagnostics: dict[str, Any],
    *,
    config: RagConfig,
    backend: str,
    query_terms: set[str],
    ranked: list[dict[str, Any]],
) -> None:
    mode = config.retrieval_diagnostics_mode.strip().lower()
    if mode not in {"summary", "verbose"}:
        return

    diagnostics["backend"] = backend
    diagnostics["query_terms"] = sorted(query_terms)

    if mode != "verbose":
        return

    limit = max(1, int(config.retrieval_diagnostics_top_n))
    explanations: list[dict[str, Any]] = []
    for item in ranked[:limit]:
        explanations.append(
            {
                "chunk_id": str(item.get("chunk_id", "")),
                "source": str(item.get("source", "")),
                "score": float(item.get("score", 0.0)),
                "components": item.get("score_components", {}),
            }
        )
    diagnostics["final_rank_explanations"] = explanations


def _score_tfidf(
    query_terms: set[str],
    candidates: list[dict[str, Any]],
    config: RagConfig,
    *,
    tabular_intent: bool,
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

        metadata_weight = _metadata_weight(chunk, config)
        boilerplate_penalty = _boilerplate_penalty_factor(chunk, config)
        table_boost = _table_boost_factor(
            query_terms,
            chunk,
            tabular_intent=tabular_intent,
            config=config,
        )
        source_work_boost = _source_work_boost_factor(query_terms, chunk)
        final_score = similarity * metadata_weight * boilerplate_penalty * table_boost * source_work_boost

        if final_score < config.min_retrieval_score:
            continue

        with_score = dict(chunk)
        with_score["score"] = round(final_score, 4)
        with_score["score_components"] = _rank_score_components(
            base_similarity=similarity,
            metadata_weight=metadata_weight,
            boilerplate_penalty=boilerplate_penalty,
            table_boost=table_boost,
            source_work_boost=source_work_boost,
            final_score=final_score,
        )
        weighted.append(with_score)

    weighted.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return weighted


def _build_vector_embedder(config: RagConfig) -> VectorEmbedder:
    adapter = config.vector_backend_adapter.strip().lower()
    if adapter == "hashing":
        return HashingVectorEmbedder(
            dimension=config.vector_dimension,
            use_char_ngrams=config.vector_use_char_ngrams,
            char_ngram_min=config.vector_char_ngram_min,
            char_ngram_max=config.vector_char_ngram_max,
        )

    # Fallback keeps backend operational even for unsupported adapter names.
    return HashingVectorEmbedder(
        dimension=config.vector_dimension,
        use_char_ngrams=config.vector_use_char_ngrams,
        char_ngram_min=config.vector_char_ngram_min,
        char_ngram_max=config.vector_char_ngram_max,
    )


def _score_vector(
    query_text: str,
    query_terms: set[str],
    candidates: list[dict[str, Any]],
    config: RagConfig,
    embedder: VectorEmbedder,
    *,
    tabular_intent: bool,
) -> list[dict[str, Any]]:
    weighted: list[dict[str, Any]] = []
    if not query_text.strip() or not candidates:
        return weighted

    query_vector = embedder.embed(query_text)
    if not query_vector:
        return weighted

    for chunk in candidates:
        text = str(chunk.get("text", ""))
        if not text.strip():
            continue
        similarity = _vector_similarity(query_vector, embedder.embed(text), config.vector_similarity_metric)

        metadata_weight = _metadata_weight(chunk, config)
        boilerplate_penalty = _boilerplate_penalty_factor(chunk, config)
        table_boost = _table_boost_factor(
            query_terms,
            chunk,
            tabular_intent=tabular_intent,
            config=config,
        )
        source_work_boost = _source_work_boost_factor(query_terms, chunk)
        final_score = similarity * metadata_weight * boilerplate_penalty * table_boost * source_work_boost

        if final_score < config.min_retrieval_score:
            continue

        with_score = dict(chunk)
        with_score["score"] = round(final_score, 4)
        with_score["score_components"] = _rank_score_components(
            base_similarity=similarity,
            metadata_weight=metadata_weight,
            boilerplate_penalty=boilerplate_penalty,
            table_boost=table_boost,
            source_work_boost=source_work_boost,
            final_score=final_score,
        )
        weighted.append(with_score)

    weighted.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return weighted


def _vector_similarity(left: list[float], right: list[float], metric: str) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    normalized_metric = metric.strip().lower()
    if normalized_metric in {"dot", "dot_product"}:
        return sum(a * b for a, b in zip(left, right))

    if normalized_metric in {"euclidean", "l2"}:
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
        return 1.0 / (1.0 + distance)

    return cosine_similarity(left, right)


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
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    response = retrieve_via_interface(query, chunks, config, thesaurus)
    return response.ranked_chunks, response.diagnostics


class LexicalRetriever(Retriever):
    """Default retrieval backend used by the current public baseline."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        tabular_intent = is_tabular_intent(request.query, request.thesaurus)
        if not query_terms:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        ranked = _score_lexical(
            query_terms,
            candidates,
            request.config,
            tabular_intent=tabular_intent,
        )
        retained = ranked[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        _attach_retrieval_diagnostics(
            diagnostics,
            config=request.config,
            backend="lexical",
            query_terms=query_terms,
            ranked=retained,
        )
        return RetrievalResponse(ranked_chunks=retained, diagnostics=diagnostics)


class TfidfRetriever(Retriever):
    """TF-IDF cosine similarity backend for retrieval."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        tabular_intent = is_tabular_intent(request.query, request.thesaurus)
        if not query_terms:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        ranked = _score_tfidf(
            query_terms,
            candidates,
            request.config,
            tabular_intent=tabular_intent,
        )
        retained = ranked[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        _attach_retrieval_diagnostics(
            diagnostics,
            config=request.config,
            backend="tfidf",
            query_terms=query_terms,
            ranked=retained,
        )
        return RetrievalResponse(ranked_chunks=retained, diagnostics=diagnostics)


class HybridRrfRetriever(Retriever):
    """Hybrid retriever that fuses lexical and TF-IDF ranking using RRF."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        tabular_intent = is_tabular_intent(request.query, request.thesaurus)
        if not query_terms:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        lexical = _score_lexical(
            query_terms,
            candidates,
            request.config,
            tabular_intent=tabular_intent,
        )
        tfidf = _score_tfidf(
            query_terms,
            candidates,
            request.config,
            tabular_intent=tabular_intent,
        )
        fused = _rrf_fuse(lexical, tfidf, request.config)
        retained = fused[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        _attach_retrieval_diagnostics(
            diagnostics,
            config=request.config,
            backend="hybrid_rrf",
            query_terms=query_terms,
            ranked=retained,
        )
        return RetrievalResponse(ranked_chunks=retained, diagnostics=diagnostics)


class VectorRetriever(Retriever):
    """Vector retriever using a pluggable embedding adapter boundary."""

    def __init__(self, embedder: VectorEmbedder | None = None) -> None:
        self._embedder = embedder

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        query_terms = expand_query_terms(request.query, request.thesaurus)
        tabular_intent = is_tabular_intent(request.query, request.thesaurus)
        query_text = request.query.strip()
        if query_terms:
            # Expanded terms enrich the vector query while preserving adapter agnosticism.
            query_text = " ".join(sorted(query_terms))
        if not query_text:
            return RetrievalResponse(ranked_chunks=[], diagnostics=_empty_diagnostics())

        lifecycle_store = LifecycleStateStore(request.config.lifecycle_state_path)
        candidates, diagnostics = _apply_lifecycle_filters(
            request.chunks,
            request.config,
            lifecycle_store,
        )

        embedder = self._embedder or _build_vector_embedder(request.config)
        ranked = _score_vector(
            query_text,
            query_terms,
            candidates,
            request.config,
            embedder,
            tabular_intent=tabular_intent,
        )
        retained = ranked[: request.config.top_k]
        diagnostics["retained"] = len(retained)
        _attach_retrieval_diagnostics(
            diagnostics,
            config=request.config,
            backend="vector",
            query_terms=query_terms,
            ranked=retained,
        )
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
        elif backend == "vector":
            active_retriever = VectorRetriever()
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
