# ShakespeareTest Branch TODO

This file tracks branch-specific work for Shakespeare-only ingestion testing.

## Scope

- Branch scope is Shakespeare corpus testing only.
- Use humanities-style overlay behavior as baseline.
- Focus on generating candidate metadata before final ingestion decisions.

## Findings-Driven TODO (For Main Branch Porting)

- [x] Add parser coverage for XML and legacy DOC inputs.
- [x] Add explicit unsupported-format diagnostics during ingestion.
- [x] Fix doc type fallback so placeholder values do not bypass taxonomy inference.
- [x] Tighten prose vs tabular heuristics to reduce false tabular classification.
- [x] Reduce chunk payload bloat by separating document-level and chunk-level metadata propagation.
- [x] Add a non-persistent ingestion mode for exploratory/test runs.
- [x] Add ingestion diagnostics output contract (per-file parser, skip reason, chunk counts, inferred type summary).
- [x] Add mixed-format ingestion regression tests for parser coverage, type inference, and chunk-shape sanity.

## Branch Execution TODO

- [ ] Add additional Shakespeare files in mixed formats under data/.
- [ ] Re-run ingestion after each parser/heuristic change and snapshot diagnostics.
- [ ] Track metadata candidate quality (doc_type, source unit boundaries, extraction method, lifecycle fields).
- [ ] Confirm changes remain framework-safe before proposing main-branch merges.
