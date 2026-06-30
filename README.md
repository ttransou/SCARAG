# SCARAG
Schema-Centric Agnostic RAG (Retrieval-Augmented Generation)

## Metadata-first RAG for any domain, and supported format

### T. Transou - June 2026



SCARAG is a configurable framework for document-grounded retrieval and answer synthesis.

The included runtime is a reference stack: a single FastAPI/Uvicorn process that serves API endpoints and built React assets.


## What the Name Means

  SCARAG = Schema-Centric Agnostic RAG

**Schema-Centric:**
-The framework prioritizes field semantics, provenance metadata, and lifecycle signals over naive document-only parsing.
-Retrieval and ground quality improve when data meaning is explicit.
**Agnostic:**
-Domain-agnostic: finance, legal, insurance, IT, test results, and other domains can all be tailored through profiles.
-Format-agnostic: the same framework core works across text, tabular, and mixed document formats.
**RAG:**
-Retrieval-Augmented Generation remains the operational pattern.
-Answers are expected to stay anchored to retrieved evidence and provenance.

The name also reflects scar tissue from prior naive approaches: hard-earned lessons turned into explicit framework design principles.



## Executive Summary

Most RAG projects fail in the same places: weak grounding, unclear provenance, poor domain fit, and brittle one-off implementation choices. This framework addresses those failure modes with reusable primitives for ingestion, chunking, retrieval tuning, confidence signaling, lifecycle/freshness policy, and evidence presentation.

Why this matters:
 - It separates framework concerns from implementation concerns.
 - It makes domain adaptation explicit instead of implicit.
 - It keeps answers accountable to source evidence.
 - It supports iterative evaluation before and after domain tailoring.

How this is useful in practice:
- Start with shared framework defaults and a reference runtime.
- Apply human-owned NLP tailoring for vocabulary, ontology, and policy.
- Validate behavior with domain datasets and metrics.
- Evolve implementation-specific provider, deployment, and UX layers without rewriting framework core.

In short: this framework is a reusable RAG foundation that helps teams move faster while preserving traceability, control, and domain fit.


## Architecture at a Glance
Insert Mermaid diagram



## Reality Snapshot
- Included reference UI target: desktop browser
- Evidence UX contract is answer-first with source-on-demand citations in a right-side drawer.
- Dense evidence handling is implemented:
  - repeated citation cards are deduped
  - low-signal citations are collapsed by default
  - collapsed evidence remains available on demand
- Generation modes available:
  - `extractive` (default)
  - `mock` (deterministic offline model)
  - `live` (adapter hook exists; provider integration is intentionally implementation-specific)
- The React layer is reference only and can be replaced or reshaped by implementers.


## Run Reference Stack (React + Uvicorn)
The React frontend under `frontend/` is a reference interface for exercising framework APIs and evidence contracts.

Prerequisites:
- Python virtual environment at `.venv` with project dependencies installed
- Node.js available for frontend build
- A local corpus under `data/` (override with `RAG_DATA_PATH`)

Build frontend once (or after UI changes):
  ```bash
  cd frontend
  npm install
  npm run build
```
Run unified server from repo root:
  ```bash
  .\.venv\Scripts\python -m uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```
One-command startup script:
```bash
powershell -ExecutionPolicy Bypass -File .\scripts\start_everything.ps1
```
Common options:
```bash
powershell -ExecutionPolicy Bypass -File .\scripts\start_everything.ps1 -SkipFrontendBuild
powershell -ExecutionPolicy Bypass -File .\scripts\start_everything.ps1 -Domain finance -TopK7
powershell -ExecutionPolicy Bypass -File .\scripts\start_everything.ps1 -GenerationMode mock
```
Endpoints:
```bash
http://127.0.0.1:8000 for React UI
http://127.0.0.1:8000/api/health for API health
```
Reference API endpoint:
```bash
POST /api/chat with body { "query": "..."}
Current response contract includes:
- message.text
- message.citations_summary (count, total_count, hidden_count, label)
- citations (visible cards)
- collapsed_citations (hidden-by-default cards)
- answer (full backend answer text)
```
Frontend principles charter:
```bash
docs/frontend-principles.md
```
Human-owned NLP tailoring guide:
```bash
docs/nlp-tailoring-guide.md
```
Example Azure deployment pattern (implementation-specific)
- Run the API layer in Azure Container Apps
- Use Azure AI Search as a cloud retrieval backend
- Store documents and ingestion artifacts in Azure Blob Storage
- Keep lifecycle metadata and audit state in Blob sidecars or Cosmos DB
- Use Microsoft Entra ID for authentication and Managed Identity for service access
- Send telemetry to Application Insights
