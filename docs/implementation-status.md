# SCARAG Implementation Status

This document tracks implementation progress for the framework surfaces described in README.

## Scope
- distinguish implemented behavior from roadmap targets,
- list implementation deltas by subsystem,
- record milestone-level status updates.

## Current Baseline
- Default branch runtime profile is now `shakespeare_test`, with API and evaluation entry points loading the Shakespeare overlay unless explicitly overridden.
- Core ingestion, chunking, lexical retrieval, lifecycle persistence, and API/UI reference surfaces are present.
- Ingestion parser coverage now includes XML (`.xml`) and legacy DOC (`.doc`) paths in the baseline loader.
- Ingestion diagnostics now report explicit per-file parser and skip reasons, including unsupported-format and internal-artifact skips.
- Canonical evidence/metadata schema and retrieval interface contracts are implemented on main.
- Tabular chunking preserves repeated-header context in per-chunk metadata.
- Chunking overlap policy is formalized by chunk type with normalized defaults for prose and tabular windows.
- Prose chunking applies configurable lexical cohesion segmentation into source units before chunk windowing.
- Chunk metadata preserves source-unit boundaries and now separates compact document-level metadata (`document_metadata`) from chunk-level metadata to reduce payload duplication.
- Doc type fallback behavior now treats placeholder values (for example `unknown`, `tbd`, `n/a`) as unset so taxonomy inference still runs.
- Tabular-vs-prose classification heuristics are tightened to reduce false tabular classification for delimiter-heavy prose.
- Non-persistent ingestion mode is available for exploratory/test runs via `ingestion_persist_lifecycle_state=False`.
- Confidence resolver scoring is implemented as a baseline, including configurable temporal decay based on lifecycle timestamps and framework-level intent alignment adjustments.
- TF-IDF retrieval backend, vector retrieval backend (adapter-based hashing baseline), and hybrid RRF scaffold are implemented baselines.
- Retrieval similarity metrics are configurable for lexical scoring (overlap/jaccard/containment) and vector scoring (cosine/dot/euclidean).
- Retrieval metadata weighting is configurable beyond doc_type-only weighting.
- Retrieval scoring applies configurable boilerplate penalties using persisted repetition signals.
- Retrieval scoring applies table-aware boosting tied to tabular intent and row/header matches.
- Retrieval diagnostics output mode includes query terms, pruning counters, and final rank explanations.
- Citation-quality enforcement is implemented before API citation emission.
- Tabular grounding baseline now includes schema-style fallback guardrails, PDF-table limits, and spreadsheet row-faithfulness through chunk metadata.
- Generation now exposes a baseline grounded-answer contract: structured abstention reason codes and citation shaping aligned to the evidence units directly used in the answer.
- API responses now expose a stable `contract_version` and repository docs now include migration notes for envelope field evolution.
- API now exposes `GET /api/ingestion/diagnostics` with per-file parser/skip diagnostics, chunk counts, and inferred doc-type summaries.
- Fallback scaffold behavior is now integration-tested for priority ordering: explicit FAQ mapping overrides intent matching, and generic fallback remains the terminal default.
- Deployment boundaries are now explicitly documented as framework-owned versus implementation-owned responsibilities (`docs/deployment-boundaries.md`).
- Environment assumptions for Python/Node, corpus layout, and startup commands are now documented in `README.md`.
- Framework base ontology is defined in `config/scarag_base_ontology.json` and wired through the default profile taxonomy overlay.
- Profile loading validates `taxonomy.concepts_path` presence and required SCARAG ontology concepts at startup.
- Framework-generic doc_type taxonomy is defined in `config/scarag_doc_type_taxonomy.json` and wired through profile `taxonomy.doc_type_taxonomy_path`.
- Profile retrieval overlays apply `preferred_doc_types` and `lower_priority_doc_types` as doc_type metadata weighting overrides.
- Mixed-format ingestion regression coverage now validates parser coverage, placeholder doc-type inference behavior, chunk-shape sanity, and diagnostics contract shape.

## Update Rule
When a roadmap target moves to partial or implemented, update this file and the capability matrix in README in the same change set.
