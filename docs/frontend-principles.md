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