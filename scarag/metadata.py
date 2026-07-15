from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


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
    table_metadata: list[dict[str, Any]] | None = None
    image_markers: list[dict[str, Any]] | None = None

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
            "table_metadata": self.table_metadata,
            "image_markers": self.image_markers,
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
