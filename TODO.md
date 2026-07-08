# SCARAG Development TODO

## P0 — robustness and clarity now
- [x] Formalize the reference UI contract for answer, citations, evidence drawer behavior, and provenance display
- [x] Document the expected frontend state model for chat messages, citations, feedback, confidence flags, and view switching
- [x] Clarify which behaviors are baseline framework expectations versus implementation-specific UX choices
- [x] Expand the README into a clearer contributor guide for the reference stack
- [x] Add a maintainer checklist for updating docs when new UI or evaluation capabilities are introduced
- [ ] Capture known gaps between the reference UI and the full implementation guidance in the documentation
- [ ] Define explicit abstention and confidence policies for low-evidence or near-match situations
- [ ] Add a structured evidence schema for source identity, chunk metadata, freshness, and confidence signals

## P1 — maturity and extensibility next
- [ ] Define a roadmap for feedback capture, persistence, and analytics hooks
- [ ] Review whether the current FAQ and feedback scaffolds should remain template-only or become configurable assets
- [ ] Add a short checklist for expected provenance and confidence signals in answers
- [ ] Document how evaluation outputs should be surfaced in the UI and in developer workflows
- [ ] Add a simple onboarding section for local development and common commands
- [ ] Note any environment assumptions for Python, Node, and local corpus setup
- [ ] Develop a layered evaluation plan covering retrieval quality, provenance completeness, abstention behavior, faithfulness, and citation support
- [ ] Document conflict and version-handling behavior for superseded, duplicate, or contradictory evidence
- [ ] Preserve the citation and evidence response contract while replacing or extending the reference UI
- [ ] Add implementation-specific validation datasets and benchmark runners in domain or implementation branches
- [ ] Integrate a live generation provider through the generation-mode adapter hook
- [ ] Add deployment-specific observability, authentication, and policy layers around the framework core

## P2 — UI minutiae and shell polish later
- [ ] Tighten spacing, hierarchy, and affordances in the reference shell
- [ ] Add a short visual polish checklist for implementers who want a tighter framework look
- [ ] Clarify which UI tweaks should stay framework-neutral versus implementation-branded
- [ ] Capture any follow-up tweaks to the drawer, badges, and empty states once the shell is exercised further

## Fallback template for chat interface
- [ ] Add scaffold file `fallback_template.json` with common fallback question/answer pairs for the chat interface. Include multiple fallback types: clarification prompts, graceful "I don't know" answers, action suggestions, and redirect/resource suggestions.
- [ ] Wire `fallback_template.json` into the runtime fallback handler (e.g., a `scripts/fallbacks.py` or `scripts/use_fallbacks.js`) so the chat UI can load and serve fallback responses when retrieval fails, confidence is low, or user intent is unclear.
- [ ] Add a small integration test or manual test checklist demonstrating the fallback selection logic and override priorities (explicit FAQ mapping > intent-based match > generic fallback).
- [ ] Allow deployment-specific overrides (e.g., env var or config path) so teams can customize fallback content without editing the repo scaffold.

### Example fallback_template.json scaffold (see `fallback_template.json` in repo root)

- The scaffold file should be a JSON array of objects. Suggested fields:
  - `id` (string): stable identifier for the fallback entry
  - `question_examples` (array): example user phrasings that should map to this fallback
  - `response` (string): the text to return to the user
  - `type` (string): one of `clarify`, `abstain`, `suggest`, `resource`, `escalate`
  - `confidence_threshold` (number, optional): a threshold below which this fallback will trigger
  - `notes` (string, optional): authoring notes for maintainers


## External citations and attribution
- [ ] Maintain a running bibliography of relevant RAG, grounding, citation, and evaluation papers and tools
- [ ] Record the core rationale for each cited work in the context of SCARAG’s design goals
- [ ] Ensure new framework claims or implementation notes are backed by cited sources where appropriate
