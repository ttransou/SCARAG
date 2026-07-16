# SCARAG Maintainer Checklist

Use this checklist before merging changes that affect UI behavior, evidence presentation, evaluation capabilities, or contributor workflows.

## 1. Scope and ownership

- Confirm which layer changed: framework core, API contract, reference UI, docs, or scripts.
- Confirm the owning files were updated in the same change set.
- Confirm implementation-specific decisions are not presented as framework requirements.

## 2. UI capability changes

If a change introduces or alters UI behavior, verify all applicable items:

- Update `docs/reference-ui-contract.md` if response usage or evidence surface behavior changed.
- Update `docs/frontend-state-model.md` if local state atoms, message shape, or view switching changed.
- Update `docs/frontend-principles.md` if baseline versus implementation-specific behavior changed.
- Update `README.md` if startup flow, ports, or local run guidance changed.
- Update `TODO.md` if a related roadmap or polish item was completed or added.

## 3. Evaluation capability changes

If a change introduces or alters evaluation behavior, verify all applicable items:

- Update `docs/evaluation-blueprint.md` for new metrics, layer definitions, or expected signals.
- Ensure evaluation outputs remain interpretable in terms of retrieval, provenance, lifecycle, grounding, and abstention behavior.
- Document any new assumptions, limitations, or implementation boundaries in `README.md`.
- Update `TODO.md` roadmap items tied to evaluation maturity.

## 4. API and evidence contract checks

- Verify `POST /api/chat` response fields still match documented contract.
- Confirm citation visibility and collapsed evidence behavior still align with docs.
- Confirm confidence labels remain documented and consistent with UI display behavior.

## 5. Local run and developer ergonomics

- Verify root startup path works: `bash ./start_everything.sh`.
- Verify UI endpoint and API health endpoint in docs are correct.
- Ensure any new scripts or command changes are reflected in contributor guidance.

## 5.1 Fallback integration checks

If fallback template entries or loader selection logic changed, verify all applicable items:

- Confirm fallback priority remains `explicit FAQ mapping > intent match > generic fallback`.
- Run fallback integration tests in `tests/test_fallbacks.py`.
- Confirm `fallback_template.json` retains a valid `generic_fallback` entry as safe default.
- Update `TODO.md` and implementation status docs when fallback verification coverage changes.

## 6. Verification checks before merge

- Run frontend build when UI code or styles changed.
- Run API tests when API surface or contract behavior changed.
- Prefer absolute paths in CI or terminal checks when working-directory drift is likely.

## 7. Release-note hygiene

- Summarize user-visible behavior changes in plain language.
- Summarize maintainer-facing doc updates.
- Call out any follow-up TODO items if work is intentionally partial.