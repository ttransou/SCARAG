# SCARAG Lifecycle Design

This document specifies lifecycle and freshness behavior for active framework development.

## Current Public Baseline
- basic source metadata propagation on chunks,
- file-backed lifecycle state store in place (source_unit_id, timestamps, status, soft-delete mark field),
- lifecycle metadata propagated onto indexed chunks.
- retrieval lifecycle policy filtering implemented (soft-delete, status allow/deny, freshness cutoff, explicit missing/invalid timestamp policy),
- retrieval lifecycle diagnostics counters exposed.

## Roadmap Targets
- lifecycle audit timelines and reporting utilities.

## Policy Direction
Lifecycle policy should remain implementation-tunable while preserving framework-level evidence governance guarantees.

## Lifecycle Metadata Model (Baseline + Target Extension)
The current baseline supports source-unit lifecycle records for ingest, update, soft-delete, and retrieval filtering decisions.

Recommended lifecycle fields:
- source_unit_id: stable identity for a source unit across ingest cycles,
- content_fingerprint: content hash used to detect unchanged units,
- ingestion_iso_ts: first time this source unit entered the system,
- last_upsert_iso_ts: most recent accepted upsert time,
- deletion_mark_iso_ts: soft-delete marker timestamp when applicable,
- status: implementation-defined lifecycle state (for example active, retired, pending_review),
- lifecycle_event_log: append-only event trail for audit and debugging (roadmap extension).

## Retrieval Policy Semantics (Implemented Baseline)
When lifecycle controls are enabled, retrieval should apply lifecycle policy before final ranking output.

Recommended policy order:
1. Exclude soft-deleted units by default.
2. Apply status allow-list or deny-list filtering when configured.
3. Apply freshness threshold checks using last_upsert_iso_ts, then ingestion_iso_ts fallback.
4. If timestamp fields are missing or invalid, default policy should be explicit and implementation-configurable.

Current baseline implementation:
- retrieval-side lifecycle filtering is active by default,
- status and freshness behavior is tunable via retrieval config,
- missing/invalid timestamp policy is explicit (include or exclude),
- lifecycle filter diagnostics counters are available from retrieval diagnostics output.

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

Current baseline implementation includes retrieval-time counters for:
- filtered_soft_deleted,
- filtered_status_allow_list,
- filtered_status_deny_list,
- filtered_freshness_stale,
- filtered_freshness_missing_timestamp,
- filtered_freshness_invalid_timestamp,
- filtered_missing_source_unit_id,
- filtered_missing_persisted_record.

## Implementation Milestones
- M1: add lifecycle metadata fields to chunk records and persisted state. (Implemented baseline)
- M2: add retrieval-side lifecycle and freshness filters behind explicit config flags. (Implemented baseline)
- M2a: harden lifecycle filtering policy semantics and add diagnostics counters. (Implemented)
- M3: add soft-delete semantics and lifecycle audit reporting.
- M4: add compliance tests for freshness/status policy behavior.
