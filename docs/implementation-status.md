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
- Confidence resolver scoring is implemented as a baseline.
- TF-IDF retrieval backend and hybrid RRF scaffold are implemented baselines; vector backend remains a roadmap target.

## Update Rule
When a roadmap target moves to partial or implemented, update this file and the capability matrix in README in the same change set.
