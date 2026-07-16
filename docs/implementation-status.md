# SCARAG Implementation Status

This document tracks implementation progress for the framework surfaces described in README.

## Scope
- distinguish implemented behavior from roadmap targets,
- list implementation deltas by subsystem,
- record milestone-level status updates.

## Current Baseline
- Core ingestion, chunking, lexical retrieval, lifecycle persistence, and API/UI reference surfaces are present.
- Canonical evidence/metadata schema and retrieval interface contracts are implemented on main.
- Tabular chunking preserves repeated-header context in per-chunk metadata.
- Chunking overlap policy is formalized by chunk type with normalized defaults for prose and tabular windows.
- Prose chunking applies configurable lexical cohesion segmentation into source units before chunk windowing.
- Chunk metadata preserves source-unit boundaries and propagates ingestion metadata into retrieval outputs.
- Confidence resolver scoring is implemented as a baseline, including configurable temporal decay based on lifecycle timestamps and framework-level intent alignment adjustments.
- TF-IDF retrieval backend, vector retrieval backend (adapter-based hashing baseline), and hybrid RRF scaffold are implemented baselines.
- Retrieval similarity metrics are configurable for lexical scoring (overlap/jaccard/containment) and vector scoring (cosine/dot/euclidean).
- Retrieval metadata weighting is configurable beyond doc_type-only weighting.
- Retrieval scoring applies configurable boilerplate penalties using persisted repetition signals.
- Retrieval scoring applies table-aware boosting tied to tabular intent and row/header matches.
- Retrieval diagnostics output mode includes query terms, pruning counters, and final rank explanations.

## Update Rule
When a roadmap target moves to partial or implemented, update this file and the capability matrix in README in the same change set.
