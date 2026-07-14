# SCARAG Metadata Model

This document defines the canonical evidence schema used from ingestion through retrieval and answer presentation.

## Objectives
- keep source identity stable,
- preserve provenance fields across the pipeline,
- support lifecycle, freshness, and confidence overlays.

## Canonical Evidence Unit Schema (Implemented)
Required fields on every chunk/evidence unit:
- chunk_id
- source
- source_unit_id
- text
- doc_type
- domain_area
- is_tabular
- content_fingerprint
- extraction_method
- extraction_ts
- ingestion_iso_ts
- last_upsert_iso_ts
- deletion_mark_iso_ts
- status
- confidence_inputs

## Confidence Input Contract (Implemented Baseline)
Current confidence input payload on evidence units:
- base_extraction_tier
- lifecycle_status
- has_deletion_mark
- tabular_evidence

These values are intentionally lightweight baseline inputs for a future resolver and are emitted to keep schema boundaries stable.

## Schema Boundaries
- ingestion is responsible for extraction metadata (extraction_method, extraction_ts),
- lifecycle state is responsible for source-unit timestamps and status,
- retrieval consumes canonical fields without mutating identity metadata,
- answer generation consumes retrieved evidence and may add view-level shaping only.

## Notes
- lifecycle_event_log remains a roadmap extension,
- confidence resolver scoring remains roadmap work; only input field generation is implemented in the baseline.
- provenance completeness validator is implemented for required source and citation fields.
