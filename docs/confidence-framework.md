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

## Conflict-Handling Policy

Contradictory evidence is a grounding problem first and a generation problem second.

Baseline policy:

- treat contradiction as disagreement across independently retrievable source units, not merely different wording;
- prefer not to synthesize a single decisive claim when top evidence supports incompatible factual states;
- keep contradictory citations visible rather than collapsing them into a single blended citation;
- lower confidence when contradiction is unresolved, and abstain when the answer would otherwise overstate one side.

Operational stages:

1. Detect candidate conflict when top-ranked chunks with adequate provenance assert incompatible values, statuses, dates, or policy directives for the same subject.
2. Preserve both sides in the evidence set when each passes provenance and citation-quality checks.
3. Prefer explicit answer framing such as "sources disagree" or abstention over silent arbitration when no framework-owned tie-break rule exists.
4. Allow implementation-specific tie-break overlays only when they are explicit, auditable, and domain-owned.

Framework-owned tie-break order:

- active lifecycle state over retired or soft-deleted state;
- newer upsert timestamp over older timestamp when both sources are otherwise comparable;
- structured/tabular evidence over weaker extraction tiers when the query depends on exact values;
- if the conflict remains unresolved after these checks, preserve both citations and lower confidence.

Non-goals for the public baseline:

- do not invent domain-specific adjudication rules;
- do not hide contradictory evidence to simplify the UI;
- do not treat fluent synthesis as evidence resolution.

Intent-aware confidence roadmap constraint:
- framework core should only use implementation-neutral intent signals (for example tabular intent and evidence-shape alignment),
- do not hardcode domain-specific confidence policies in framework baseline,
- domain-specific confidence behavior belongs in optional overlays/profiles.

## Contract Boundary
The baseline now emits confidence inputs at indexing time. Resolver scoring remains a separate roadmap stage so confidence policy can evolve without breaking evidence schema contracts.

## Design Principle
Confidence is an evidence-governance signal, not a fluency proxy.
