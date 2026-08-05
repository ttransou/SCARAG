from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


REFERENCE_METADATA_FIELDS = (
    "title",
    "author",
    "document_type",
    "act",
    "scene",
    "stanza",
    "section",
    "page",
    "speaker",
    "attributed_person",
    "stage_cue",
    "line_start",
    "line_end",
    "passage_start",
    "passage_end",
    "source",
    "edition",
)

CONTEXT_METADATA_FIELDS = (
    "composition_date",
    "publication_or_performance_date",
    "genre",
    "historical_setting",
    "alternate_titles",
    "edition_history",
    "related_works",
)

INTERPRETIVE_METADATA_FIELDS = (
    "themes",
    "interpretive_traditions",
    "disputed_classifications",
    "commentary_links",
    "critical_essays",
    "editorial_notes",
    "claims_with_source_attribution",
)

METADATA_TIER_FIELDS: dict[str, tuple[str, ...]] = {
    "reference": REFERENCE_METADATA_FIELDS,
    "context": CONTEXT_METADATA_FIELDS,
    "interpretive": INTERPRETIVE_METADATA_FIELDS,
}


CANONICAL_EVIDENCE_FIELDS = (
    "chunk_id",
    "source",
    "source_unit_id",
    "text",
    "doc_type",
    "domain_area",
    "is_tabular",
    "content_fingerprint",
    "extraction_method",
    "extraction_ts",
    "ingestion_iso_ts",
    "last_upsert_iso_ts",
    "deletion_mark_iso_ts",
    "status",
    "confidence_inputs",
)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_metadata_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        normalized_items = [_normalize_metadata_value(item) for item in value]
        filtered = [item for item in normalized_items if item is not None]
        return filtered or None
    if isinstance(value, dict):
        normalized_dict = {
            str(key).strip(): normalized
            for key, raw_value in value.items()
            if str(key).strip()
            for normalized in [_normalize_metadata_value(raw_value)]
            if normalized is not None
        }
        return normalized_dict or None
    normalized = str(value).strip()
    return normalized or None


def _tier_payload_from_mapping(mapping: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field_name in fields:
        normalized = _normalize_metadata_value(mapping.get(field_name))
        if normalized is not None:
            payload[field_name] = normalized
    return payload


def build_verification_states(
    *,
    metadata: Any = None,
    metadata_tiers: Any = None,
    doc_type: str,
    source: str,
    source_work_title: str | None = None,
    explicit_metadata: Any = None,
) -> dict[str, Any] | None:
    flat_metadata = metadata if isinstance(metadata, dict) else {}
    explicit_input = explicit_metadata if isinstance(explicit_metadata, dict) else {}
    explicit_tiers = metadata_tiers if isinstance(metadata_tiers, dict) else {}
    reference_tier = {}

    for field_name in REFERENCE_METADATA_FIELDS:
        if field_name in explicit_input:
            explicit_value = explicit_input.get(field_name)
            normalized_explicit = _normalize_metadata_value(explicit_value)
            if normalized_explicit is not None:
                reference_tier[field_name] = {
                    "value": normalized_explicit,
                    "state": "exact",
                }
                continue

        explicit_reference = explicit_tiers.get("reference") if isinstance(explicit_tiers.get("reference"), dict) else {}
        explicit_tier_value = explicit_reference.get(field_name)
        normalized_explicit_tier = _normalize_metadata_value(explicit_tier_value)
        if normalized_explicit_tier is not None:
            reference_tier[field_name] = {
                "value": normalized_explicit_tier,
                "state": "normalized",
            }
            continue

        direct_value = flat_metadata.get(field_name)
        normalized_direct = _normalize_metadata_value(direct_value)
        if normalized_direct is not None:
            reference_tier[field_name] = {
                "value": normalized_direct,
                "state": "inferred",
            }
            continue

        if field_name == "document_type" and doc_type:
            reference_tier[field_name] = {
                "value": doc_type,
                "state": "inferred",
            }
        elif field_name == "source" and source:
            reference_tier[field_name] = {
                "value": source,
                "state": "inferred",
            }
        elif field_name == "title" and source_work_title and source_work_title.lower() != "unknown":
            reference_tier[field_name] = {
                "value": source_work_title,
                "state": "inferred",
            }
        else:
            reference_tier[field_name] = {
                "value": None,
                "state": "missing",
            }

    return {"reference": reference_tier} if reference_tier else None


def build_metadata_tiers(
    *,
    metadata: Any = None,
    metadata_tiers: Any = None,
    doc_type: str,
    source: str,
    source_work_title: str | None = None,
) -> dict[str, dict[str, Any]] | None:
    flat_metadata = metadata if isinstance(metadata, dict) else {}
    explicit_tiers = metadata_tiers if isinstance(metadata_tiers, dict) else {}

    tiers: dict[str, dict[str, Any]] = {}
    for tier_name, tier_fields in METADATA_TIER_FIELDS.items():
        tier_payload = _tier_payload_from_mapping(flat_metadata, tier_fields)
        explicit_payload = explicit_tiers.get(tier_name)
        if isinstance(explicit_payload, dict):
            tier_payload.update(_tier_payload_from_mapping(explicit_payload, tier_fields))
        if tier_payload:
            tiers[tier_name] = tier_payload

    reference_tier = dict(tiers.get("reference", {}))
    if source_work_title and not reference_tier.get("title"):
        reference_tier["title"] = source_work_title
    if doc_type and not reference_tier.get("document_type"):
        reference_tier["document_type"] = doc_type
    if source and not reference_tier.get("source"):
        reference_tier["source"] = source
    if reference_tier:
        tiers["reference"] = reference_tier

    return tiers or None


@dataclass(frozen=True)
class EvidenceMetadata:
    chunk_id: str
    source: str
    source_unit_id: str
    text: str
    doc_type: str
    domain_area: str
    is_tabular: bool
    content_fingerprint: str
    extraction_method: str
    extraction_ts: str
    ingestion_iso_ts: str
    last_upsert_iso_ts: str
    deletion_mark_iso_ts: str | None
    status: str
    confidence_inputs: dict[str, Any]
    tabular_chunk_metadata: dict[str, Any] | None = None
    prose_chunk_metadata: dict[str, Any] | None = None
    source_unit_local_id: str | None = None
    source_unit_kind: str | None = None
    source_unit_boundary: dict[str, Any] | None = None
    document_metadata: dict[str, Any] | None = None
    source_work_key: str | None = None
    source_work_title: str | None = None
    source_work_tokens: list[str] | None = None
    source_format: str | None = None
    boilerplate_signal: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "source_unit_id": self.source_unit_id,
            "text": self.text,
            "doc_type": self.doc_type,
            "domain_area": self.domain_area,
            "is_tabular": self.is_tabular,
            "content_fingerprint": self.content_fingerprint,
            "extraction_method": self.extraction_method,
            "extraction_ts": self.extraction_ts,
            "ingestion_iso_ts": self.ingestion_iso_ts,
            "last_upsert_iso_ts": self.last_upsert_iso_ts,
            "deletion_mark_iso_ts": self.deletion_mark_iso_ts,
            "status": self.status,
            "confidence_inputs": self.confidence_inputs,
            "tabular_chunk_metadata": self.tabular_chunk_metadata,
            "prose_chunk_metadata": self.prose_chunk_metadata,
            "source_unit_local_id": self.source_unit_local_id,
            "source_unit_kind": self.source_unit_kind,
            "source_unit_boundary": self.source_unit_boundary,
            "document_metadata": self.document_metadata,
            "source_work_key": self.source_work_key,
            "source_work_title": self.source_work_title,
            "source_work_tokens": self.source_work_tokens,
            "source_format": self.source_format,
            "boilerplate_signal": self.boilerplate_signal,
        }


def extraction_tier_for_method(extraction_method: str) -> str:
    method = extraction_method.strip().lower()
    if any(key in method for key in ("xlsx", "csv", "json")):
        return "structured_parse"
    if any(key in method for key in ("docx", "pptx", "pdf", "html", "mhtml")):
        return "document_parse"
    return "plain_text_parse"


def build_confidence_inputs(
    *,
    extraction_method: str,
    status: str,
    deletion_mark_iso_ts: str | None,
    is_tabular: bool,
) -> dict[str, Any]:
    return {
        "base_extraction_tier": extraction_tier_for_method(extraction_method),
        "lifecycle_status": status,
        "has_deletion_mark": bool(deletion_mark_iso_ts),
        "tabular_evidence": bool(is_tabular),
    }


def missing_canonical_fields(record: dict[str, Any]) -> list[str]:
    return [field for field in CANONICAL_EVIDENCE_FIELDS if field not in record]
