# SCARAG Confidence Framework

This document defines confidence assessment design and rollout stages.

## Current Public Baseline
- lightweight confidence signal in API responses: high, low, abstain.
- confidence input fields emitted on evidence metadata: base_extraction_tier, lifecycle_status, has_deletion_mark, tabular_evidence.
- confidence resolver module computes confidence from retrieval score + extraction tier + lifecycle signal + evidence coverage.
- confidence resolver applies configurable temporal decay using lifecycle timestamps (last_upsert_iso_ts with ingestion fallback).
- confidence resolver applies configurable intent-aware adjustment factors from framework-level intent/evidence alignment (for example tabular intent vs tabular evidence shape).

## Roadmap Targets
- domain overlay support,
- confidence debug traces for diagnosis.
- richer intent-aware scoring diagnostics.

Intent-aware confidence roadmap constraint:
- framework core should only use implementation-neutral intent signals (for example tabular intent and evidence-shape alignment),
- do not hardcode domain-specific confidence policies in framework baseline,
- domain-specific confidence behavior belongs in optional overlays/profiles.

## Contract Boundary
The baseline now emits confidence inputs at indexing time. Resolver scoring remains a separate roadmap stage so confidence policy can evolve without breaking evidence schema contracts.

## Design Principle
Confidence is an evidence-governance signal, not a fluency proxy.
