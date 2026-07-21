# Deployment Boundaries

## Purpose

This document clarifies deployment responsibilities between framework-owned SCARAG surfaces and implementation-owned deployment decisions.

SCARAG provides deployable reference components, but it does not prescribe a single production topology.

## Framework-owned deployment surfaces (this repo)

- API and response contract behavior in `api_server.py`.
- Core ingestion, retrieval, lifecycle, confidence, and grounding behavior under `scarag/`.
- Reference startup scripts (`start_everything.sh`, `scripts/start_everything.sh`, `scripts/start_everything.ps1`).
- Reference UI shell in `frontend/` and expected API interaction envelope.
- Offline evaluation workflow and report generation in `scripts/run_eval.py`.

These surfaces are maintained as baseline framework capabilities and may be used as a local deployment starting point.

## Implementation-owned deployment surfaces (downstream)

- Cloud or on-prem topology design.
- Container/image strategy and orchestration.
- Authentication, authorization, and secret management.
- Observability stack (logging, metrics, traces, alerting).
- Network controls, gateway policy, and rate limiting.
- Data retention, backup, and disaster recovery policy.
- Provider-specific live model integration and runtime controls.
- Domain policy workflows (ontology governance, confidence overlay governance, approval flows).

These choices are intentionally implementation-specific and should not be treated as framework-core defaults.

## Practical boundary rules

1. Framework docs should describe capability contracts and baseline behavior, not mandate a cloud vendor.
2. Implementation docs should define production topology, SLOs, security controls, and operational ownership.
3. Changes to framework-owned runtime contracts should be reflected in `README.md`, `docs/implementation-status.md`, and related contract docs in the same change set.
4. Implementation-specific deployment customizations should be isolated from core framework claims in roadmap and status docs.

## Reference local baseline

The local baseline for this repository remains:

- API: FastAPI app from `api_server.py`.
- UI: React reference shell from `frontend/`.
- Startup: `bash ./start_everything.sh`.

This local baseline is a development and validation path, not a production deployment prescription.