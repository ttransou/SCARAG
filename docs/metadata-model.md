# SCARAG Metadata Model

This document defines the metadata schema used from ingestion through retrieval and answer presentation.

## Objectives
- keep source identity stable,
- preserve provenance fields across the pipeline,
- support lifecycle, freshness, and confidence overlays.

## Baseline Fields (Current Public)
- source
- chunk_id
- source_unit_id
- doc_type
- domain_area
- is_tabular
- content_fingerprint
- ingestion_iso_ts
- last_upsert_iso_ts
- deletion_mark_iso_ts
- status

## Roadmap Targets
- extraction_method
- extraction_ts
- ingestion_iso_ts
- last_upsert_iso_ts
- deletion_mark_iso_ts
- status
- confidence_debug fields
