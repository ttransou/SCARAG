# SCARAG Implementation TODO

## Purpose
This file tracks implementation work needed to reconcile the public framework baseline with the README's architectural intent while preserving SCARAG philosophy: schema before generation, provenance before fluency, domain tailoring before generic automation, and abstention before unsupported synthesis.

## Status Legend
- **Implemented:** implemented in current public code and validated by tests/docs.
- **Partial:** implemented in simplified form; key behavior or robustness gaps remain.
- **Roadmap target:** required for core implementation; not yet implemented.
- **Design/specification:** intentionally postponed until dependencies or design decisions are complete.
- **Future extension:** useful beyond core implementation or implementation-specific.

## Immediate Priorities
Dependency order is intentional. Complete top to bottom to unlock downstream work.
Branch timing and branch-cut dependencies are tracked separately in Branching Gates (Set Aside).

1. [ ] Roadmap target (Foundational): Mature framework-first contracts on main (schema boundaries, lifecycle semantics, confidence inputs, and retrieval interfaces).
2. [ ] Roadmap target (Foundational): Define and implement canonical evidence/metadata schema in code and docs.
3. [ ] Roadmap target (Foundational): Add lifecycle persistence model (source_unit_id, timestamps, status, soft-delete marks).
4. [x] Implemented (Foundational): Wire retrieval-side lifecycle/freshness/status filters against persisted state.
5. [ ] Roadmap target (Foundational): Implement confidence resolver that consumes extraction + lifecycle signals.
6. [ ] Roadmap target (Foundational): Add TF-IDF/vector retrieval path and hybrid rerank scaffold.
7. [ ] Roadmap target: Strengthen tabular grounding from intent-only guardrail to matched-row evidence policy.
8. [ ] Roadmap target: Expand evaluation datasets/metrics to cover new lifecycle/confidence/tabular behavior.
9. [ ] Roadmap target: Add contract-stability tests for API envelope and citation shaping.

## Branching Gates (Set Aside)
These items are intentionally tracked outside Immediate Priorities and should be evaluated when framework-main milestones are ready.

1. [ ] Roadmap target (Foundational): Define explicit branch-cut criteria for when foundational framework work is stable enough to branch.
2. [ ] Roadmap target (Foundational): Create a framework feature branch only after criteria in #1 are met.

## Capability Backlog

### 1. Evidence / Metadata Schema
- [ ] Partial: Chunk records currently include source, chunk_id, doc_type, domain_area, is_tabular, content_fingerprint.
- [ ] Roadmap target (Foundational): Define canonical evidence unit schema in docs/metadata-model.md with required and optional fields.
- [ ] Roadmap target (Foundational): Add source_unit_id to ingestion/chunk pipeline for stable source-unit identity.
- [ ] Roadmap target (Foundational): Add extraction_method and extraction_ts metadata on all extracted units.
- [ ] Roadmap target (Foundational): Add lifecycle fields ingestion_iso_ts, last_upsert_iso_ts, deletion_mark_iso_ts, status.
- [ ] Roadmap target: Add confidence input fields expected by resolver (base extraction tier, temporal features, intent flags).
- [ ] Roadmap target: Add provenance completeness validator that checks required citation and source fields.

### 2. Ingestion
- [ ] Partial: Supports txt, md, json, csv, html/htm, mhtml/mht, pdf, docx, pptx, xlsx/xls loading.
- [ ] Roadmap target: Add recursive JSON flattening (nested dict/list path expansion) instead of shallow key:value rendering.
- [ ] Partial: DOCX/PPTX/XLSX text extraction exists; table extraction strategy is simplistic.
- [ ] Roadmap target: Add explicit DOCX/PPTX/XLSX table extraction metadata (table_id, row_index, header fields).
- [ ] Roadmap target: Improve PDF table handling beyond text-layer extraction heuristics.
- [ ] Partial: MHTML parser handles basic text/html part extraction; multipart robustness gaps remain.
- [ ] Roadmap target: Add image marker propagation where non-text objects are encountered.
- [ ] Partial: .xls path currently routed through openpyxl; verify and harden legacy .xls behavior or provide converter fallback.
- [ ] Roadmap target: Emit extraction_method metadata for every parser path.

### 3. Chunking
- [ ] Implemented: Prose chunking with chunk_size, overlap, min_chunk_words.
- [ ] Partial: Tabular chunking uses row windows and overlap but assumes first line header.
- [ ] Roadmap target: Preserve repeated headers explicitly in tabular chunk metadata.
- [ ] Roadmap target: Formalize overlap policy by chunk type (prose vs tabular) and document defaults.
- [ ] Design/specification: Lexical cohesion splitting exists as config concept but is not implemented in chunking logic.
- [ ] Roadmap target: Preserve source-unit boundaries so chunks can trace to precise source units.
- [ ] Roadmap target: Ensure full chunk metadata propagation from ingestion through retrieval output.

### 4. Retrieval
- [ ] Implemented: Query expansion from config/synonyms.json.
- [ ] Implemented: Score threshold and top_k controls in lexical retrieval.
- [ ] Roadmap target (Foundational): Add TF-IDF retrieval backend with explicit normalization behavior.
- [ ] Roadmap target (Foundational): Add vector retrieval backend behind configurable adapter boundary.
- [ ] Design/specification: Similarity metric options beyond current lexical overlap pending vector backend.
- [ ] Partial: Metadata weighting currently doc_type-only.
- [ ] Roadmap target: Add boilerplate penalties once repeated boilerplate signals are persisted.
- [ ] Roadmap target: Add table-aware boosting tied to tabular intent and row/header matches.
- [ ] Roadmap target: Add reranking strategies including RRF and lexical/semantic hybrid blending.
- [ ] Roadmap target: Add retrieval diagnostics output mode for query terms, candidate pruning, and final rank explanations.

### 5. Governance / Lifecycle / Freshness
- [ ] Partial (Foundational): Persist ingestion timestamps and upsert timestamps per source_unit_id (baseline store + chunk propagation implemented).
- [ ] Partial: Persist deletion marks and status values in lifecycle state (fields and store semantics implemented; retrieval filtering still pending).
- [ ] Partial (Foundational): Implement persistent re-ingestion state store (file-backed baseline implemented; audit/reporting hardening pending).
- [ ] Roadmap target: Add skip-unchanged behavior controlled by explicit flag and audit logging.
- [x] Implemented: Exclude soft-deleted units by default from retrieval.
- [x] Implemented: Add freshness filtering based on lifecycle timestamps.
- [x] Implemented: Add status filtering allow-list/deny-list controls.
- [ ] Roadmap target: Implement lifecycle audit reporting utility.
- [ ] Design/specification: Hard cleanup utility for permanently purging soft-deleted state.

### 6. Confidence / Provenance
- [ ] Partial: API emits high/low/abstain confidence signal.
- [ ] Roadmap target (Foundational): Implement confidence resolver module and integrate into pipeline.
- [ ] Roadmap target: Define extraction confidence tiers and mapping from extraction_method.
- [ ] Roadmap target: Add domain confidence overlays in profile configs.
- [ ] Roadmap target: Add temporal decay support in confidence scoring.
- [ ] Roadmap target: Add intent-based confidence boosting/penalties.
- [ ] Design/specification: Conflict-handling policy for contradictory evidence sources.
- [ ] Partial: Provenance fields in citations exist; completeness enforcement is missing.
- [ ] Roadmap target: Add citation quality checks (snippet adequacy, source traceability, duplicate policy).

### 7. Tabular Grounding
- [ ] Partial: Table intent detection exists via thesaurus intent group.
- [ ] Partial: Abstention when tabular intent has no tabular evidence is implemented.
- [ ] Roadmap target: Enforce strict row-grounded answering for tabular intent.
- [ ] Roadmap target: Add matched-row evidence selection and trace output.
- [ ] Roadmap target: Define schema-style fallback policy and hard guardrails.
- [ ] Partial: XLSX/XLS ingestion path exists; row-faithfulness guarantees are incomplete.
- [ ] Roadmap target: Define explicit PDF table behavior and limits for grounded tabular answers.
- [ ] Roadmap target: Add evaluation coverage for tabular intent success and abstention correctness.

### 8. Generation
- [ ] Implemented: Extractive mode baseline.
- [ ] Implemented: Mock mode baseline.
- [ ] Partial: Live adapter hook exists as placeholder response.
- [ ] Future extension: Provider-specific live integration is implementation-owned, not framework-core.
- [ ] Roadmap target: Define grounded answer contract (allowed synthesis boundaries and citation obligations).
- [ ] Partial: Abstention messages exist; policy taxonomy and reason codes are missing.
- [ ] Partial: Citation shaping exists in API; generation-citation coupling is shallow.

### 9. API / Response Contract
- [ ] Implemented: /api/health and /api/chat endpoints exist.
- [ ] Implemented: Response envelope includes message, citations_summary, citations, collapsed_citations, answer, confidence.
- [ ] Partial: Legacy payload compatibility exists in UI normalization path (sources fallback), not fully contract-tested.
- [ ] Roadmap target: Add explicit contract tests for envelope fields and type stability.
- [ ] Roadmap target: Add tests for citation summary count semantics and collapsed-citation behavior.
- [ ] Roadmap target: Version contract changes with documented migration notes when fields evolve.

### 10. Reference UI
- [ ] Implemented: Answer-first display with source drawer pattern.
- [ ] Partial: Citation dedup/collapse behavior is split between backend and UI; needs unified policy doc.
- [ ] Implemented: Feedback placeholder and FAQ template view exist.
- [ ] Implemented: Theme toggle exists.
- [ ] Roadmap target: Document whether FAQ and feedback scaffolds remain template-only or become configurable assets.
- [ ] Roadmap target: Improve accessibility (keyboard nav, aria review, contrast checks, focus order).
- [ ] Partial: Implementation-neutral UI guidance exists; add explicit do/don't list for framework vs brand customization.
- [ ] Roadmap target: Document how evaluation outputs should be surfaced in the reference UI and developer workflow.
- [ ] Design/specification: UI polish tasks that do not affect framework contract fidelity.
- [ ] Design/specification: Tighten spacing, hierarchy, and affordances in the reference shell.
- [ ] Design/specification: Add a short visual polish checklist for implementers.
- [ ] Design/specification: Clarify framework-neutral vs implementation-branded UI tweaks.
- [ ] Design/specification: Capture follow-up tweaks to drawer behavior, badge treatment, and empty states after additional shell usage.

### 11. Evaluation
- [ ] Partial: Offline runner and report generation implemented in scripts/run_eval.py.
- [ ] Roadmap target: Create canonical, regression, and drift datasets under eval/datasets.
- [ ] Roadmap target: Add implementation-specific validation datasets and benchmark runners in domain/implementation branches.
- [ ] Implemented: hit_rate, MRR, context_precision, provenance_completeness, abstention_rate, tabular_grounding_compliance metrics in runner.
- [ ] Roadmap target: Add lifecycle compliance and freshness compliance metrics after lifecycle controls are implemented.
- [ ] Roadmap target: Add faithfulness_proxy and correctness_proxy metrics or remove references consistently.
- [ ] Roadmap target: Add dataset sanity checks and malformed-row reporting.
- [ ] Partial: reset_eval_workspace.py exists for cleanup; extend docs for repeatable test-data cleanup protocol.

### 12. Domain Profiles / NLP Tailoring
- [ ] Partial: profiles/default.json loads through RagConfig.from_profile.
- [ ] Implemented: Domain thesaurus support via config/synonyms.json.
- [ ] Roadmap target: Add profile overlays for retrieval/lifecycle/confidence defaults.
- [ ] Roadmap target: Add ontology/taxonomy template examples and integration guidance.
- [ ] Roadmap target: Expand doc_type taxonomy behavior and domain-specific overrides.
- [ ] Roadmap target: Add confidence overlay file conventions and loader behavior.
- [ ] Design/specification: Domain kickoff worksheet file (implementation aid; not core runtime).
- [ ] Future extension: Implementation-specific pruning workflow for single-domain deployments.

### 13. Docs / Repository Hygiene
- [ ] Partial: README implementation status and capability matrix are in place.
- [ ] Implemented: Path consistency fixes for current package layout (scarag/, api_server.py, frontend/, scripts/, docs/).
- [ ] Implemented: Contributor guide and maintainer checklist exist.
- [ ] Partial: Architecture docs set now exists (implementation-status, metadata-model, lifecycle-design, retrieval-design, confidence-framework, tabular-grounding).
- [ ] Roadmap target: Keep README capability statuses synchronized with code changes in every feature PR.
- [ ] Roadmap target: Add deployment notes with explicit framework-owned vs implementation-owned boundaries.
- [ ] Roadmap target: Add environment assumptions section (Python, Node, corpus layout, startup commands).
- [ ] Roadmap target: Record core rationale for each bibliography item in context of SCARAG design goals.
- [ ] Roadmap target: Ensure new framework claims and implementation notes are backed by citations where appropriate.

### Fallback Integration
- [ ] Partial: fallback_template.json scaffold and scripts/fallbacks.py runtime loader are implemented.
- [ ] Roadmap target: Add integration test or manual checklist for fallback priority (explicit FAQ mapping > intent match > generic fallback).

## Implementation-Specific Boundaries
- [ ] Future extension: Live model provider integrations, cloud deployment topology, auth, and observability are implementation-specific by design.
- [ ] Roadmap target: Keep framework-core TODOs separate from implementation-specific tasks in future backlog updates.

## Trace Log: Previously Checked-Off Items
This log preserves items that were checked off in earlier TODO iterations before the roadmap backlog rewrite/checklist normalization.

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
