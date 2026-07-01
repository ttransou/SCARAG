# Frontend Principles

- Keep the UI answer-first and source-on-demand.
- Prefer a right-side evidence drawer for citations.
- Deduplicate repeated citation cards and collapse low-signal evidence by default.

# Local UI State
The frontend must consist of:
- main left panel collapsed/expanded data
- trace/citation drawer under retrieved response, collapsed/expanded data
- theme mode (default|light|dark)

# Design Intent
The UI built around a different but typical RAG chat interface. In many RAG apps, users see a polished answer and small source list. SCARAG must show more "working surfaces" to establish transparency, confidence, and source documentation.
- which documents, pages, paragraphs, or chunks were retrieved to generate the plain-language response
- ratings on RAGAS evals and metrics
- generated flags for low confidence but close cosine similarity

# Information Architecture
The UI has two persistent regions (optional)
- left panel: identity, API health status, navigations actions (New Chat, Chat History, FAQ, Support)
- center panel: conversation viewport, FAQ viewport

## Inline Answer Transparency
Answer rendering supports:
- headings, lists, tables, code, inline emphasis
- citations/sources drawer with links to source document, citation
- scoring of response

# Feedback
Allowing a simple thumbs up/down and feedback capturing feature per use case is helpful for the implementer's future refinement/enhancements.