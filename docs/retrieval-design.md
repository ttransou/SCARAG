# SCARAG Retrieval Design

This document captures retrieval architecture and tuning guidance for active framework development.

## Current Public Baseline
- lexical overlap scoring,
- doc_type-aware weighting,
- thesaurus-based query expansion,
- top_k and min_retrieval_score controls.

## Roadmap Targets
- TF-IDF or vector retrieval backend,
- hybrid retrieval blending,
- reranking strategies with diagnostics,
- retrieval behavior profiling by domain.

## Diagnostic Expectations
Evaluation should isolate retrieval failure from generation failure and report ranking behavior transparently.
