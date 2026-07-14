# SCARAG Lifecycle Design

This document specifies lifecycle and freshness behavior for reconstruction.

## Current Public Baseline
- basic source metadata propagation on chunks,
- no persistent lifecycle state store.

## Reconstruction Targets
- persistent re-ingestion state,
- freshness filtering controls,
- soft-delete lifecycle markers,
- lifecycle audit timelines.

## Policy Direction
Lifecycle policy should remain implementation-tunable while preserving framework-level evidence governance guarantees.

## Lifecycle Metadata Model (Target)
The reconstruction target is a source-unit lifecycle record that supports ingest, update, skip, soft-delete, and retrieval filtering decisions.

Recommended lifecycle fields:
- source_unit_id: stable identity for a source unit across ingest cycles,
- content_fingerprint: content hash used to detect unchanged units,
- ingestion_iso_ts: first time this source unit entered the system,
- last_upsert_iso_ts: most recent accepted upsert time,
- deletion_mark_iso_ts: soft-delete marker timestamp when applicable,
- status: implementation-defined lifecycle state (for example active, retired, pending_review),
- lifecycle_event_log: append-only event trail for audit and debugging.

## Retrieval Policy Semantics (Target)
When lifecycle controls are enabled, retrieval should apply lifecycle policy before final ranking output.

Recommended policy order:
1. Exclude soft-deleted units by default.
2. Apply status allow-list or deny-list filtering when configured.
3. Apply freshness threshold checks using last_upsert_iso_ts, then ingestion_iso_ts fallback.
4. If timestamp fields are missing or invalid, default policy should be explicit and implementation-configurable.

## Re-ingestion Behavior (Target)
Re-ingestion should preserve long-lived identity while refreshing update state.

Expected behavior:
- unchanged content: retain ingestion timestamp and optionally skip indexing,
- changed content for existing source_unit_id: retain ingestion_iso_ts and update last_upsert_iso_ts,
- newly observed source unit: initialize ingestion and upsert timestamps,
- soft-delete operation: mark deletion timestamp without removing audit history.

## Audit and Diagnostics (Target)
Lifecycle diagnostics should be inspectable through reports or APIs and should include:
- number of active, soft-deleted, and filtered units,
- freshness-filter exclusion counts,
- status-filter exclusion counts,
- re-ingestion event counts (created, updated, unchanged-skipped),
- invalid or missing timestamp counts.

## Reconstruction Milestones
- M1: add lifecycle metadata fields to chunk records and persisted state.
- M2: add retrieval-side lifecycle and freshness filters behind explicit config flags.
- M3: add soft-delete semantics and lifecycle audit reporting.
- M4: add compliance tests for freshness/status policy behavior.
