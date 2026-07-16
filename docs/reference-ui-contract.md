# SCARAG Reference UI Contract

This document defines the reference UI contract for the SCARAG stack. It is the baseline behavior expected by the repository's FastAPI backend and React reference frontend.

## Scope

The contract covers the answer surface, citation surface, evidence drawer behavior, and provenance display for the desktop reference UI.

It does not define implementation-specific polish, deployment branding, or application-specific feedback storage.

## Response Envelope

`POST /api/chat` returns a JSON object with these top-level fields:

- `contract_version`: stable framework contract version for the response envelope
- `message`: the UI-facing message envelope
- `citations`: the visible citation cards
- `collapsed_citations`: citation cards hidden by default but still available on demand
- `confidence`: the current answer confidence signal
- `answer`: the full answer text shown in the conversation viewport

Legacy compatibility note:

- the reference frontend still accepts a legacy `sources` array as a fallback when `citations` is absent;
- framework-owned contract tests should continue to prefer the modern `citations` payload and treat `sources` support as compatibility behavior, not the primary contract.

## Contract Versioning

Current baseline contract version: `1.0`

Versioning rules:

- increment the major version when a consumer would need code changes to remain compatible;
- increment the minor version when adding optional fields without breaking existing consumers;
- preserve documented compatibility fallbacks during migration windows where feasible.

Migration notes for field evolution are tracked in [docs/api-contract-migrations.md](api-contract-migrations.md).

The `message` object contains:

- `text`: the rendered answer text
- `citations_summary`: a compact summary of visible and hidden evidence
- `tabular_trace` (optional): grounding diagnostics for tabular-intent handling
- `generation` (optional baseline diagnostics): generation grounding policy, abstention state, reason code, and cited chunk ids

`citations_summary` contains:

- `count`: number of visible citations
- `total_count`: total number of retrieved citations
- `hidden_count`: number of hidden citations
- `label`: short human-readable summary

`generation` contains:

- `grounding_policy`: baseline generation mode such as extractive grounding or tabular row grounding
- `abstained`: whether the answer generator refused to make a grounded claim
- `reason_code`: stable baseline reason code when abstention or placeholder behavior occurs
- `used_context_count`: number of evidence units directly used to produce the answer text
- `cited_chunk_ids`: ordered chunk ids used by the generator and expected to align with citation shaping

## Assistant Message State

The reference frontend treats assistant messages as the primary answer surface. Each assistant message may include:

- rendered answer text
- a citation list for the active answer
- a confidence badge
- an optional score badge
- thumbs up/down feedback state
- a draft feedback field when thumbs-down is selected

User messages remain plain text.

## Evidence Drawer Behavior

The reference UI is answer-first and source-on-demand.

Required behavior:

- show the answer in the main conversation viewport first
- open the evidence drawer automatically after a new query is submitted
- render citations in a right-side drawer
- deduplicate repeated citation cards before rendering
- collapse low-signal evidence by default when there is no separate hidden set
- keep collapsed evidence available for later inspection
- display an empty state when no evidence has been surfaced yet
- keep the visible and collapsed citation sets aligned with the evidence units the generator actually used for the answer, not the full retrieved set

The drawer should always show the currently active assistant message's evidence, not a blended history of all answers.

## Unified Citation Dedup/Collapse Policy

The framework baseline uses a single policy with clear ownership boundaries so citation behavior is stable across backend and reference UI.

### Backend-owned responsibilities

- enforce required citation fields and citation-quality checks before emission
- enforce duplicate collapse by `(chunk_id, normalized document)` and keep the first retained citation
- shape response evidence into:
	- `citations`: visible set shown by default
	- `collapsed_citations`: retained-but-hidden set available on demand
- emit `message.citations_summary` counts derived from the post-quality, post-dedup citation set

### UI-owned responsibilities

- treat backend `citations` and `collapsed_citations` as authoritative in modern (`contract_version` 1.x) payloads
- render visible citations first and keep collapsed citations inspectable through a secondary drawer section or reveal action
- do not re-rank or merge backend citations in ways that change provenance identity
- preserve order from backend payloads so reviewers can compare UI evidence with API diagnostics

### Legacy fallback responsibilities

When only legacy `sources` are provided, the reference UI may apply a compatibility normalization path. In that mode:

- local dedup/collapse heuristics are allowed as compatibility behavior
- compatibility behavior must not be treated as the primary framework contract
- once modern `citations` payloads are present, backend-owned shaping rules above take precedence

## Citation Quality Policy

The backend baseline now enforces citation-quality checks before citations reach the visible or collapsed sets.

Required baseline checks:

- snippet adequacy: a citation snippet must contain enough textual substance to let a reviewer inspect support rather than a fragmentary token or label;
- source traceability: a citation's chunk identifier and document path must resolve back to a retained source chunk;
- duplicate policy: repeated citations for the same chunk/document pair should collapse to the first retained citation rather than appear multiple times.

UI consequence:

- the reference frontend should treat backend-visible and backend-collapsed citations as already quality-screened;
- if contradictory evidence survives quality checks, show the separate citations rather than merging them into one card.

## Provenance Display

Each visible citation card should present enough provenance for a reviewer to trace the answer back to source evidence.

The reference contract expects the following citation fields when available:

- `id`: stable citation identifier
- `title`: short source label
- `document`: source path or document identifier
- `snippet`: supporting evidence excerpt
- `score`: retrieval score or ranking signal
- `chunk_id`: underlying chunk identifier
- `doc_type`: document type or source classification
- `tabular_grounded`: whether citation evidence passed row-grounding policy for tabular intent
- `matched_row_count`: number of matched rows used from the citation chunk
- `matched_terms`: query terms matched against row/header evidence

The UI should link to the source when a usable link is available. If no link is present, the reference frontend may use a placeholder link, but implementation stacks should prefer a resolvable source target.

## Confidence Semantics

The reference UI exposes confidence as a display signal, not as a hard policy engine.

Recommended meanings:

- `high`: evidence is present and the answer is grounded
- `low`: evidence is present but weak or sparse
- `abstain`: the system should avoid overclaiming because evidence is insufficient
- `offline`: the backend is unreachable
- `ready` / `reviewing sources...`: transient UI states used during interaction

Implementations may add more specific confidence labels, but the reference UI should preserve the textual signal and show it in the answer chrome and evidence drawer.

## Evaluation Signal Surfacing

Evaluation diagnostics should be available per assistant response, but remain lightweight and non-intrusive for routine users.

Baseline UI guidance:

- show eval indicators near citations/evidence, not in the primary answer text block
- keep indicators minimal (for example: pass/warn badges, short metric labels, or compact status chips)
- make each indicator clickable to select a diagnostic scope for on-demand detail viewing
- default to collapsed/hidden evaluation detail panels so users who do not care about eval are not burdened
- keep citation review and evaluation review co-located in the evidence drawer to reduce context switching

Reference drawer pattern:

- render compact eval chips in a small evaluation strip above citation cards
- place detailed diagnostics in a collapsed "Advanced eval diagnostics" section below citation cards
- require explicit user action for detail reveal (select chip, then expand advanced section)
- keep the advanced section optional and visually secondary to citation inspection

Contract boundary:

- framework baseline defines placement and interaction pattern (minimal + clickable + optional)
- implementations define visual treatment, exact metric set, and storage/telemetry wiring

## Abstention Reason Codes

The baseline framework now emits stable generation-level reason codes for abstention or placeholder states.

Current baseline codes:

- `no_supporting_evidence`: no retained evidence survived into generation
- `usable_evidence_missing`: evidence was retrieved but had no usable text for extractive grounding
- `tabular_row_evidence_missing`: tabular intent lacked matched row evidence
- `live_adapter_unconfigured`: live mode was requested but no implementation adapter exists in framework baseline

These codes are diagnostics for contract consumers and evaluation. They do not replace the top-level `confidence` label.

## Baseline Versus Implementation-Specific

Baseline framework expectations:

- answer-first presentation
- visible citations and hidden collapsed citations
- evidence drawer for provenance review
- confidence and score display surfaces
- feedback scaffolding in the assistant message card

Implementation-specific choices:

- visual theme and branding
- FAQ content and navigation labels
- feedback persistence and analytics
- exact citation ordering rules beyond the visible/collapsed split
- source-link generation strategy

FAQ and feedback scaffold policy:

- FAQ starts as a reference template in framework baseline and should be configurable by domain implementations to match use-case language, workflows, and policy context
- feedback controls are baseline scaffold UX; persistence targets, routing, analytics, and moderation are implementation-specific configurable assets

## Change Rule

If the backend response shape or the reference UI evidence surface changes, update this document in the same change set.
