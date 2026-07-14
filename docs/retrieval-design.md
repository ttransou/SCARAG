# SCARAG Retrieval Design

This document captures retrieval architecture and tuning guidance for active framework development.

## Current Public Baseline
- lexical overlap scoring,
- doc_type-aware weighting,
- thesaurus-based query expansion,
- top_k and min_retrieval_score controls,
- retrieval interface contract boundary (request/response and retriever protocol) with lexical backend adapter,
- TF-IDF cosine backend with explicit normalization,
- hybrid reciprocal-rank-fusion scaffold across lexical and TF-IDF rankings.

## Roadmap Targets
- vector retrieval backend,
- reranking strategies with diagnostics,
- retrieval behavior profiling by domain.

## Interface Contract (Implemented)
Retrieval backends are expected to satisfy the Retriever protocol and return:
- ranked_chunks: ordered evidence units using canonical metadata schema,
- diagnostics: retrieval and lifecycle filter counters for explainability.

## Diagnostic Expectations
Evaluation should isolate retrieval failure from generation failure and report ranking behavior transparently.
