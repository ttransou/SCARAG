# SCARAG Confidence Framework

This document defines confidence assessment design and rollout stages.

## Current Public Baseline
- lightweight confidence signal in API responses: high, low, abstain.
- confidence input fields emitted on evidence metadata: base_extraction_tier, lifecycle_status, has_deletion_mark, tabular_evidence.
- confidence resolver module computes confidence from retrieval score + extraction tier + lifecycle signal + evidence coverage.

## Roadmap Targets
- domain overlay support,
- confidence debug traces for diagnosis.
- temporal decay and richer intent-aware scoring policies.

## Contract Boundary
The baseline now emits confidence inputs at indexing time. Resolver scoring remains a separate roadmap stage so confidence policy can evolve without breaking evidence schema contracts.

## Design Principle
Confidence is an evidence-governance signal, not a fluency proxy.
