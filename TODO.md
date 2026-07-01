# SCARAG Development TODO

## P0 — robustness and clarity now
- [ ] Formalize the reference UI contract for answer, citations, evidence drawer behavior, and provenance display
- [ ] Document the expected frontend state model for chat messages, citations, feedback, confidence flags, and view switching
- [ ] Clarify which behaviors are baseline framework expectations versus implementation-specific UX choices
- [ ] Expand the README into a clearer contributor guide for the reference stack
- [ ] Add a maintainer checklist for updating docs when new UI or evaluation capabilities are introduced
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

## External citations and attribution
- [ ] Maintain a running bibliography of relevant RAG, grounding, citation, and evaluation papers and tools
- [ ] Record the core rationale for each cited work in the context of SCARAG’s design goals
- [ ] Ensure new framework claims or implementation notes are backed by cited sources where appropriate
