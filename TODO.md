# SCARAG Reconstruction TODO

## Purpose
This file tracks implementation work needed to reconcile the public reconstruction with the README's architectural intent while preserving SCARAG philosophy: schema before generation, provenance before fluency, domain tailoring before generic automation, and abstention before unsupported synthesis.

## Status Legend
- [ ] Reconstructed: implemented in current public code and validated by tests/docs.
- [ ] Partial: implemented in simplified form; key behavior or robustness gaps remain.
- [ ] TODO: required for core reconstruction; not yet implemented.
- [ ] Deferred: intentionally postponed until dependencies or design decisions are complete.
- [ ] Future Extension: useful beyond core reconstruction or implementation-specific.

## Immediate Priorities
Dependency order is intentional. Complete top to bottom to unlock downstream work.

1. [ ] TODO (Foundational): Define and implement canonical evidence/metadata schema in code and docs.
2. [ ] TODO (Foundational): Add lifecycle persistence model (source_unit_id, timestamps, status, soft-delete marks).
3. [ ] TODO (Foundational): Wire retrieval-side lifecycle/freshness/status filters against persisted state.
4. [ ] TODO (Foundational): Implement confidence resolver that consumes extraction + lifecycle signals.
5. [ ] TODO (Foundational): Add TF-IDF/vector retrieval path and hybrid rerank scaffold.
6. [ ] TODO: Strengthen tabular grounding from intent-only guardrail to matched-row evidence policy.
7. [ ] TODO: Expand evaluation datasets/metrics to cover new lifecycle/confidence/tabular behavior.
8. [ ] TODO: Add contract-stability tests for API envelope and citation shaping.

## Capability Backlog

### 1. Evidence / Metadata Schema
- [ ] Partial: Chunk records currently include source, chunk_id, doc_type, domain_area, is_tabular, content_fingerprint.
- [ ] TODO (Foundational): Define canonical evidence unit schema in docs/metadata-model.md with required and optional fields.
- [ ] TODO (Foundational): Add source_unit_id to ingestion/chunk pipeline for stable source-unit identity.
- [ ] TODO (Foundational): Add extraction_method and extraction_ts metadata on all extracted units.
- [ ] TODO (Foundational): Add lifecycle fields ingestion_iso_ts, last_upsert_iso_ts, deletion_mark_iso_ts, status.
- [ ] TODO: Add confidence input fields expected by resolver (base extraction tier, temporal features, intent flags).
- [ ] TODO: Add provenance completeness validator that checks required citation and source fields.

### 2. Ingestion
- [ ] Partial: Supports txt, md, json, csv, html/htm, mhtml/mht, pdf, docx, pptx, xlsx/xls loading.
- [ ] TODO: Add recursive JSON flattening (nested dict/list path expansion) instead of shallow key:value rendering.
- [ ] Partial: DOCX/PPTX/XLSX text extraction exists; table extraction strategy is simplistic.
- [ ] TODO: Add explicit DOCX/PPTX/XLSX table extraction metadata (table_id, row_index, header fields).
- [ ] TODO: Improve PDF table handling beyond text-layer extraction heuristics.
- [ ] Partial: MHTML parser handles basic text/html part extraction; multipart robustness gaps remain.
- [ ] TODO: Add image marker propagation where non-text objects are encountered.
- [ ] Partial: .xls path currently routed through openpyxl; verify and harden legacy .xls behavior or provide converter fallback.
- [ ] TODO: Emit extraction_method metadata for every parser path.

### 3. Chunking
- [ ] Reconstructed: Prose chunking with chunk_size, overlap, min_chunk_words.
- [ ] Partial: Tabular chunking uses row windows and overlap but assumes first line header.
- [ ] TODO: Preserve repeated headers explicitly in tabular chunk metadata.
- [ ] TODO: Formalize overlap policy by chunk type (prose vs tabular) and document defaults.
- [ ] Deferred: Lexical cohesion splitting exists as config concept but is not implemented in chunking logic.
- [ ] TODO: Preserve source-unit boundaries so chunks can trace to precise source units.
- [ ] TODO: Ensure full chunk metadata propagation from ingestion through retrieval output.

### 4. Retrieval
- [ ] Reconstructed: Query expansion from config/synonyms.json.
- [ ] Reconstructed: Score threshold and top_k controls in lexical retrieval.
- [ ] TODO (Foundational): Add TF-IDF retrieval backend with explicit normalization behavior.
- [ ] TODO (Foundational): Add vector retrieval backend behind configurable adapter boundary.
- [ ] Deferred: Similarity metric options beyond current lexical overlap pending vector backend.
- [ ] Partial: Metadata weighting currently doc_type-only.
- [ ] TODO: Add boilerplate penalties once repeated boilerplate signals are persisted.
- [ ] TODO: Add table-aware boosting tied to tabular intent and row/header matches.
- [ ] TODO: Add reranking strategies including RRF and lexical/semantic hybrid blending.
- [ ] TODO: Add retrieval diagnostics output mode for query terms, candidate pruning, and final rank explanations.

### 5. Governance / Lifecycle / Freshness
- [ ] TODO (Foundational): Persist ingestion timestamps and upsert timestamps per source_unit_id.
- [ ] TODO: Persist deletion marks and status values in lifecycle state.
- [ ] TODO (Foundational): Implement persistent re-ingestion state store (file-backed first).
- [ ] TODO: Add skip-unchanged behavior controlled by explicit flag and audit logging.
- [ ] TODO: Exclude soft-deleted units by default from retrieval.
- [ ] TODO: Add freshness filtering based on lifecycle timestamps.
- [ ] TODO: Add status filtering allow-list/deny-list controls.
- [ ] TODO: Implement lifecycle audit reporting utility.
- [ ] Deferred: Hard cleanup utility for permanently purging soft-deleted state.

### 6. Confidence / Provenance
- [ ] Partial: API emits high/low/abstain confidence signal.
- [ ] TODO (Foundational): Implement confidence resolver module and integrate into pipeline.
- [ ] TODO: Define extraction confidence tiers and mapping from extraction_method.
- [ ] TODO: Add domain confidence overlays in profile configs.
- [ ] TODO: Add temporal decay support in confidence scoring.
- [ ] TODO: Add intent-based confidence boosting/penalties.
- [ ] Deferred: Conflict-handling policy for contradictory evidence sources.
- [ ] Partial: Provenance fields in citations exist; completeness enforcement is missing.
- [ ] TODO: Add citation quality checks (snippet adequacy, source traceability, duplicate policy).

### 7. Tabular Grounding
- [ ] Partial: Table intent detection exists via thesaurus intent group.
- [ ] Partial: Abstention when tabular intent has no tabular evidence is implemented.
- [ ] TODO: Enforce strict row-grounded answering for tabular intent.
- [ ] TODO: Add matched-row evidence selection and trace output.
- [ ] TODO: Define schema-style fallback policy and hard guardrails.
- [ ] Partial: XLSX/XLS ingestion path exists; row-faithfulness guarantees are incomplete.
- [ ] TODO: Define explicit PDF table behavior and limits for grounded tabular answers.
- [ ] TODO: Add evaluation coverage for tabular intent success and abstention correctness.

### 8. Generation
- [ ] Reconstructed: Extractive mode baseline.
- [ ] Reconstructed: Mock mode baseline.
- [ ] Partial: Live adapter hook exists as placeholder response.
- [ ] Future Extension: Provider-specific live integration is implementation-owned, not framework-core.
- [ ] TODO: Define grounded answer contract (allowed synthesis boundaries and citation obligations).
- [ ] Partial: Abstention messages exist; policy taxonomy and reason codes are missing.
- [ ] Partial: Citation shaping exists in API; generation-citation coupling is shallow.

### 9. API / Response Contract
- [ ] Reconstructed: /api/health and /api/chat endpoints exist.
- [ ] Reconstructed: Response envelope includes message, citations_summary, citations, collapsed_citations, answer, confidence.
- [ ] Partial: Legacy payload compatibility exists in UI normalization path (sources fallback), not fully contract-tested.
- [ ] TODO: Add explicit contract tests for envelope fields and type stability.
- [ ] TODO: Add tests for citation summary count semantics and collapsed-citation behavior.
- [ ] TODO: Version contract changes with documented migration notes when fields evolve.

### 10. Reference UI
- [ ] Reconstructed: Answer-first display with source drawer pattern.
- [ ] Partial: Citation dedup/collapse behavior is split between backend and UI; needs unified policy doc.
- [ ] Reconstructed: Feedback placeholder and FAQ template view exist.
- [ ] Reconstructed: Theme toggle exists.
- [ ] TODO: Document whether FAQ and feedback scaffolds remain template-only or become configurable assets.
- [ ] TODO: Improve accessibility (keyboard nav, aria review, contrast checks, focus order).
- [ ] Partial: Implementation-neutral UI guidance exists; add explicit do/don't list for framework vs brand customization.
- [ ] TODO: Document how evaluation outputs should be surfaced in the reference UI and developer workflow.
- [ ] Deferred: UI polish tasks that do not affect framework contract fidelity.
- [ ] Deferred: Tighten spacing, hierarchy, and affordances in the reference shell.
- [ ] Deferred: Add a short visual polish checklist for implementers.
- [ ] Deferred: Clarify framework-neutral vs implementation-branded UI tweaks.
- [ ] Deferred: Capture follow-up tweaks to drawer behavior, badge treatment, and empty states after additional shell usage.

### 11. Evaluation
- [ ] Partial: Offline runner and report generation implemented in scripts/run_eval.py.
- [ ] TODO: Create canonical, regression, and drift datasets under eval/datasets.
- [ ] TODO: Add implementation-specific validation datasets and benchmark runners in domain/implementation branches.
- [ ] Reconstructed: hit_rate, MRR, context_precision, provenance_completeness, abstention_rate, tabular_grounding_compliance metrics in runner.
- [ ] TODO: Add lifecycle compliance and freshness compliance metrics after lifecycle controls are implemented.
- [ ] TODO: Add faithfulness_proxy and correctness_proxy metrics or remove references consistently.
- [ ] TODO: Add dataset sanity checks and malformed-row reporting.
- [ ] Partial: reset_eval_workspace.py exists for cleanup; extend docs for repeatable test-data cleanup protocol.

### 12. Domain Profiles / NLP Tailoring
- [ ] Partial: profiles/default.json loads through RagConfig.from_profile.
- [ ] Reconstructed: Domain thesaurus support via config/synonyms.json.
- [ ] TODO: Add profile overlays for retrieval/lifecycle/confidence defaults.
- [ ] TODO: Add ontology/taxonomy template examples and integration guidance.
- [ ] TODO: Expand doc_type taxonomy behavior and domain-specific overrides.
- [ ] TODO: Add confidence overlay file conventions and loader behavior.
- [ ] Deferred: Domain kickoff worksheet file (implementation aid; not core runtime).
- [ ] Future Extension: Implementation-specific pruning workflow for single-domain deployments.

### 13. Docs / Repository Hygiene
- [ ] Partial: README reconstruction status and capability matrix are in place.
- [ ] Reconstructed: Path consistency fixes for current package layout (scarag/, api_server.py, frontend/, scripts/, docs/).
- [ ] Reconstructed: Contributor guide and maintainer checklist exist.
- [ ] Partial: Architecture docs set now exists (reconstruction-status, metadata-model, lifecycle-design, retrieval-design, confidence-framework, tabular-grounding).
- [ ] TODO: Keep README capability statuses synchronized with code changes in every feature PR.
- [ ] TODO: Add deployment notes with explicit framework-owned vs implementation-owned boundaries.
- [ ] TODO: Add environment assumptions section (Python, Node, corpus layout, startup commands).
- [ ] TODO: Record core rationale for each bibliography item in context of SCARAG design goals.
- [ ] TODO: Ensure new framework claims and implementation notes are backed by citations where appropriate.

### Fallback Integration
- [ ] Partial: fallback_template.json scaffold and scripts/fallbacks.py runtime loader are implemented.
- [ ] TODO: Add integration test or manual checklist for fallback priority (explicit FAQ mapping > intent match > generic fallback).

## Implementation-Specific Boundaries
- [ ] Future Extension: Live model provider integrations, cloud deployment topology, auth, and observability are implementation-specific by design.
- [ ] TODO: Keep framework-core TODOs separate from implementation-specific tasks in future backlog updates.

## Trace Log: Previously Checked-Off Items
This log preserves items that were checked off in earlier TODO iterations before the reconstruction backlog rewrite/checklist normalization.

### Documentation and Contract Work
- [x] Formalize the reference UI contract for answer, citations, evidence drawer behavior, and provenance display.
- [x] Document the expected frontend state model for chat messages, citations, feedback, confidence flags, and view switching.
- [x] Clarify baseline framework expectations versus implementation-specific UX choices.
- [x] Expand README into a clearer contributor guide for the reference stack.
- [x] Add a maintainer checklist for doc updates when UI/evaluation capabilities change.
- [x] Capture known gaps between the reference UI and full implementation guidance in documentation.
- [x] Define explicit abstention and confidence policies for low-evidence or near-match situations.
- [x] Add a short checklist for expected provenance and confidence signals in answers.
- [x] Add a simple onboarding section for local development and common commands.
- [x] Develop a layered evaluation plan covering retrieval quality, provenance completeness, abstention behavior, faithfulness, and citation support.
- [x] Preserve the citation and evidence response contract while replacing or extending the reference UI.

### Fallback Scaffold Work
- [x] Add fallback_template.json scaffold with clarification, abstain, suggest/resource, and escalation fallback types.
- [x] Wire fallback_template.json into runtime fallback handler via scripts/fallbacks.py.
- [x] Allow deployment-specific fallback overrides via env var or config path.

### Bibliography Baseline
- [x] Maintain a running bibliography of relevant RAG, grounding, citation, and evaluation papers/tools.
