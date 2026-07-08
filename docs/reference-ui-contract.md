# SCARAG Reference UI Contract

This document defines the reference UI contract for the SCARAG stack. It is the baseline behavior expected by the repository's FastAPI backend and React reference frontend.

## Scope

The contract covers the answer surface, citation surface, evidence drawer behavior, and provenance display for the desktop reference UI.

It does not define implementation-specific polish, deployment branding, or application-specific feedback storage.

## Response Envelope

`POST /api/chat` returns a JSON object with these top-level fields:

- `message`: the UI-facing message envelope
- `citations`: the visible citation cards
- `collapsed_citations`: citation cards hidden by default but still available on demand
- `confidence`: the current answer confidence signal
- `answer`: the full answer text shown in the conversation viewport

The `message` object contains:

- `text`: the rendered answer text
- `citations_summary`: a compact summary of visible and hidden evidence

`citations_summary` contains:

- `count`: number of visible citations
- `total_count`: total number of retrieved citations
- `hidden_count`: number of hidden citations
- `label`: short human-readable summary

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

The drawer should always show the currently active assistant message's evidence, not a blended history of all answers.

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

## Change Rule

If the backend response shape or the reference UI evidence surface changes, update this document in the same change set.
