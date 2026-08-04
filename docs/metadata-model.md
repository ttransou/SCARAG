# SCARAG Metadata Model

This document defines the canonical evidence schema used from ingestion through retrieval and answer presentation.

## Objectives
- keep source identity stable,
- preserve provenance fields across the pipeline,
- support lifecycle, freshness, and confidence overlays.

## Framework Base Ontology (Implemented Baseline)
SCARAG now ships a framework-owned baseline ontology in [config/scarag_base_ontology.json](../config/scarag_base_ontology.json).

Minimum framework concepts:
- Source
- SourceUnit
- EvidenceUnit
- DocumentType
- LifecycleStatus
- Provenance
- ConfidenceSignal
- Citation
- DomainProfile
- Concept

Core relationships:
- Source contains SourceUnit
- SourceUnit produces EvidenceUnit
- EvidenceUnit carries Metadata
- EvidenceUnit has LifecycleStatus
- EvidenceUnit has Provenance
- EvidenceUnit may support Citation
- EvidenceUnit may contribute to Answer
- DomainProfile guides retrieval, lifecycle, confidence, and vocabulary behavior

## Canonical Evidence Unit Schema (Implemented)
Required fields on every chunk/evidence unit:
- chunk_id
- source
- source_unit_id
- text
- doc_type
- domain_area
- is_tabular
- content_fingerprint
- extraction_method
- extraction_ts
- ingestion_iso_ts
- last_upsert_iso_ts
- deletion_mark_iso_ts
- status
- confidence_inputs

Optional chunk metadata fields:
- tabular_chunk_metadata (present for tabular chunks)
- prose_chunk_metadata (present for prose chunks)
- source_unit_local_id
- source_unit_kind
- source_unit_boundary
- document_metadata (compact document-level summary propagated to each chunk)

Current document_metadata baseline:
- table_count
- image_marker_count
- table_ids
- image_marker_ids
- metadata_tiers (when document-level metadata is available)

Shakespeare branch metadata tier payload (`document_metadata.metadata_tiers`):

- reference
	- title
	- author
	- document_type
	- act, scene, stanza, section, page
	- speaker or attributed_person
	- line_start, line_end, passage_start, passage_end
	- source
	- edition
- context
	- composition_date
	- publication_or_performance_date
	- genre
	- historical_setting
	- alternate_titles
	- edition_history
	- related_works
- interpretive
	- themes
	- interpretive_traditions
	- disputed_classifications
	- commentary_links
	- critical_essays
	- editorial_notes
	- claims_with_source_attribution

Placement guidance for Shakespeare Tier 1 fields:

- Document-scoped reference fields belong in `document_metadata.metadata_tiers.reference`.
- Use `document_metadata.metadata_tiers.reference` for `title`, `author`, `document_type`, `source`, and `edition`.
- Passage-scoped reference fields should remain chunk-local rather than document-global.
- Use `source_unit_kind` and `source_unit_local_id` to identify the local dramatic or poetic unit that a chunk came from.
- Use `source_unit_boundary` for location-bearing Tier 1 fields such as `act`, `scene`, `stanza`, `section`, `page`, `line_start`, `line_end`, `passage_start`, and `passage_end` when they can be derived from the source structure.
- Attach `speaker` and `attributed_person` to the same chunk-local passage metadata used for structural boundaries so they can be reviewed against the exact cited passage.
- Do not store passage-scoped values only at document level, because they become ambiguous once chunks from different scenes, speeches, or stanzas are retrieved together.

Verification expectation for inferred Tier 1 fields:

- If a field is copied directly from explicit source text, it is human-verifiable by exact text match.
- If a field is normalized from source text (for example edition wording or title cleanup), verification should confirm both the source phrase and the normalized stored value.
- If a field is heuristic or pattern-inferred, ingestion diagnostics should expose it for review rather than treating it as silently authoritative.
- If the source does not support a field cleanly, leave the field unset instead of inventing a value.

Optional document_metadata detail expansion:
- tables (full table metadata records; emitted when `chunk_include_document_level_details=True`)
- image_markers (full image marker records; emitted when `chunk_include_document_level_details=True`)

Current tabular_chunk_metadata baseline:
- section_index
- has_header
- header_text
- header_source
- header_repeat_index
- header_repeat_count
- row_start_index
- row_end_index
- window_row_count
- overlap_rows

Current prose_chunk_metadata baseline:
- chunk_start_word_index
- chunk_end_word_index
- chunk_word_count
- overlap_words
- absolute_chunk_start_word_index
- absolute_chunk_end_word_index
- cohesion_split_applied

## Confidence Input Contract (Implemented Baseline)
Current confidence input payload on evidence units:
- base_extraction_tier
- lifecycle_status
- has_deletion_mark
- tabular_evidence

These values are intentionally lightweight baseline inputs for a future resolver and are emitted to keep schema boundaries stable.

## Schema Boundaries
- ingestion is responsible for extraction metadata (extraction_method, extraction_ts),
- lifecycle state is responsible for source-unit timestamps and status,
- chunk shaping keeps chunk-level metadata (`tabular_chunk_metadata`, `prose_chunk_metadata`) separate from document-level metadata (`document_metadata`) to reduce payload bloat,
- document-level scholarly or bibliographic metadata should be supplied through `metadata` or `metadata_tiers` on ingestion records and is normalized into `document_metadata.metadata_tiers`,
- retrieval consumes canonical fields without mutating identity metadata,
- answer generation consumes retrieved evidence and may add view-level shaping only.

## Notes
- lifecycle_event_log remains a roadmap extension,
- confidence resolver scoring remains roadmap work; only input field generation is implemented in the baseline.
- provenance completeness validator is implemented for required source and citation fields.
