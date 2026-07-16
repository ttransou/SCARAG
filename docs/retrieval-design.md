# SCARAG Retrieval Design

This document captures retrieval architecture and tuning guidance for active framework development.

## Current Public Baseline
- lexical overlap scoring,
- lexical similarity metric selectors (overlap, jaccard, containment),
- configurable metadata weighting rules (doc_type baseline + extensible metadata factors),
- persisted repeated-boilerplate signals with configurable penalty factors,
- table-aware boosting tied to tabular intent and row/header evidence,
- thesaurus-based query expansion,
- top_k and min_retrieval_score controls,
- retrieval interface contract boundary (request/response and retriever protocol) with lexical backend adapter,
- TF-IDF cosine backend with explicit normalization,
- vector backend with configurable embedding adapter boundary (hashing embedder baseline),
- vector similarity metric selectors (cosine, dot, euclidean),
- hybrid reciprocal-rank-fusion scaffold across lexical and TF-IDF rankings.
- retrieval diagnostics output mode with query-term and rank-explanation surfaces.

## Roadmap Targets
- calibration tooling and deeper retrieval profiling,
- retrieval behavior profiling by domain.

## Interface Contract (Implemented)
Retrieval backends are expected to satisfy the Retriever protocol and return:
- ranked_chunks: ordered evidence units using canonical metadata schema,
- diagnostics: retrieval and lifecycle filter counters for explainability.

## Diagnostic Expectations
Evaluation should isolate retrieval failure from generation failure and report ranking behavior transparently.
