# ShakespeareTest Branch TODO

This file tracks branch-specific work for Shakespeare-only ingestion testing.

## Scope

- Branch scope is Shakespeare corpus testing only.
- Use Shakespeare-specific profile, taxonomy, and vocabulary as the active baseline.
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

## Metadata Tier TODO

- [x] Step 1: define the Tier 1 fields that must be derived directly from raw works in `data/` with no manual pre-annotation.
	- `title`
	- `author`
	- `document_type`
	- `source`
	- `edition`
	- `act`
	- `scene`
	- `stanza`
	- `section`
	- `page`
	- `speaker`
	- `attributed_person`
	- `stage_cue`
	- `line_start`
	- `line_end`
	- `passage_start`
	- `passage_end`
- [x] Step 2: implement and validate document-level inference for Tier 1 core fields: `title`, `author`, `document_type`, `source`, and `edition`.
	- [x] helper: filename and source parser
	- [x] helper: title-block and front-matter parser
	- [x] helper: work-identity normalizer
	- [x] helper: taxonomy resolver
- [x] Step 3: implement and validate passage-level inference for Tier 1 location fields from source text structure: `act`, `scene`, `stanza`, `section`, `page`, `speaker`, `attributed_person`, and line or passage boundaries.
	- helper: dramatic structure parser
	- helper: poetry structure parser
	- helper: speaker attribution parser
	- helper: stage cue parser linked to the nearest speaking unit when cues trail or interrupt dialogue
	- helper: passage boundary helper
	- helper: page marker helper
	- design choice: decide whether passage-local dramatic metadata belongs in an expanded `source_unit_boundary` payload or a dedicated dramatic-structure metadata block
- [x] Step 4: add ingestion diagnostics that show where each Tier 1 field was stored, whether it was exact, normalized, inferred, or missing, and which values require human review.
	- helper: verification-state emitter
- [x] Step 4a: ensure repeated speaker labels and stage directions are marked as dramatic structure rather than generic boilerplate for retrieval scoring.
- [x] Step 4b: emit per-field verification states for Tier 1 reference metadata so review can distinguish `exact`, `normalized`, `inferred`, and `missing`.
- [x] Step 5: define the manual curation format for Tier 2 Context metadata so bibliographic and historical fields can be attached after raw ingestion.
	- manual curation schema: `metadata_tiers.context` plus a `curation` block attached to the document record
	- required fields for manual curation: `composition_date`, `publication_or_performance_date`, `genre`, `historical_setting`, `alternate_titles`, `edition_history`, `related_works`
	- curator provenance fields: `curated_by`, `curated_at`, `source_note`, `review_status`, `confidence`
	- allowed review statuses: `draft`, `reviewed`, `approved`, `rejected`
	- storage pattern: keep branch-local context overlays as document-level metadata, not chunk-level defaults, so they can be attached after ingestion without changing baseline retrieval behavior
	- suggested file format: YAML overlay keyed by source work or source path for local curation and review, because it is more natural for narrative curator input than JSON
	- reference template: [docs/shakespeare-tier2-curation-example.yaml](docs/shakespeare-tier2-curation-example.yaml)
- [x] Step 6: define the optional manual curation format for Tier 3 Interpretive metadata so scholarly enrichment remains attributable and reviewable.
	- manual curation schema: `metadata_tiers.interpretive` plus a `curation` block attached to the document record
	- required fields for manual curation: `themes`, `interpretive_traditions`, `disputed_classifications`, `commentary_links`, `critical_essays`, `editorial_notes`, `claims_with_source_attribution`
	- curator provenance fields: `curated_by`, `curated_at`, `source_note`, `review_status`, `confidence`
	- allowed review statuses: `draft`, `reviewed`, `approved`, `rejected`
	- storage pattern: keep interpretive overlays branch-local and document-level so they remain optional and reviewable without changing baseline retrieval behavior
	- suggested file format: YAML overlay keyed by source work or source path for local curation and review
- [ ] Step 7: keep Tier 2 and Tier 3 overlays branch-local and curator-managed; do not require them for baseline Shakespeare ingestion.

## Repo Streamlining TODO

- [ ] Strip remaining framework-first branding from branch-facing docs, scripts, and UI copy.
- [ ] Switch branch-visible naming and messaging to Shakespeare/domain-specific branding where runtime behavior is already Shakespeare-only.
- [ ] Clean branch-only repo surfaces by removing stale generic or humanities carry-over guidance that no longer matches this branch.
