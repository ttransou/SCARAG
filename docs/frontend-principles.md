# Frontend Principles

This document separates baseline framework expectations from implementation-specific UX choices.

## Baseline Framework Expectations

These behaviors are part of the SCARAG reference experience and should remain recognizable across implementations:

- keep the UI answer-first and source-on-demand
- prefer a right-side evidence drawer for citations
- deduplicate repeated citation cards
- collapse low-signal evidence by default when possible
- show provenance for the retrieved evidence behind an answer
- surface confidence and score as explicit answer chrome
- provide an obvious feedback scaffold on assistant messages

## Implementation-Specific UX Choices

These are reference defaults, not framework requirements. Implementers may replace them without changing the core contract:

- visual theme details
- branding and layout polish
- FAQ content and navigation labels
- history behavior and storage
- feedback persistence and analytics hooks
- exact citation ordering beyond the visible/collapsed split
- how source links are generated

## Framework vs Brand Customization: Do/Don't

Use this list to keep framework-contract behavior intact while allowing implementation branding.

Do:

- keep answer-first rendering and source-on-demand evidence inspection
- preserve evidence provenance fields (`title`, `document`, `snippet`, and stable citation identity)
- keep confidence visible on assistant answers
- retain access to collapsed/hidden evidence when the backend provides it
- customize typography, spacing, iconography, and component styling to match brand
- replace FAQ copy, helper text, and navigation labels with implementation language

Don't:

- hide or remove provenance surfaces when an answer is shown
- silently drop citations that were emitted as visible evidence by the backend
- relabel `abstain`/low-confidence responses as high-confidence claims
- treat legacy `sources` fallback behavior as the primary API contract
- couple framework docs to implementation-only brand assets or campaign copy
- require implementation-specific analytics/feedback persistence in framework baseline UX

## Local UI State

The current reference UI keeps the following visible shell state in the component:

- main left panel collapsed or expanded state
- trace/citation drawer open or collapsed state
- theme mode (`default`, `light`, or `dark`)

## Design Intent

SCARAG uses a more transparent RAG chat interface than a simple polished answer-and-links panel. The reference UI should expose the "working surfaces" that help reviewers inspect how an answer was produced.

Those surfaces include:

- which documents, pages, paragraphs, or chunks were retrieved to generate the response
- confidence-relevant flags such as low confidence or near-match evidence
- evaluation-oriented signals when implementations choose to surface them

## Information Architecture

The reference UI uses two persistent regions when the full shell is visible:

- left panel: identity, API health status, navigation actions such as New Chat, Chat History, FAQ, and Support
- center panel: conversation viewport or FAQ viewport

## Inline Answer Transparency

Answer rendering supports:

- headings, lists, tables, code, and inline emphasis
- citations or sources in a right-side drawer
- score display when available

## Feedback

A thumbs up/down control and optional free-text feedback field are part of the reference scaffold.

Persisting that feedback is implementation-specific.

## Evaluation Output UX Pattern

- Evaluation output should be discoverable per response but visually minimal by default.
- Evaluation affordances should live with citations/evidence surfaces rather than the answer body.
- Use compact, clickable indicators to select diagnostic context.
- Keep detailed diagnostics in a collapsed advanced section under citations so detail reveal is two-step and intentional.
- Keep evaluation disclosure optional so non-evaluation users can ignore it without losing core answer/citation workflow.

## FAQ and Feedback Asset Policy

- FAQ entries in the reference UI are starter template content and should be configurable assets in domain implementations.
- FAQ configurability may be file-backed, CMS-backed, or service-backed, as long as framework contract surfaces remain intact.
- Feedback controls are baseline scaffold elements; storage, routing, and governance are implementation-specific configurable capabilities.