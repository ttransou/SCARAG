# SCARAG API Contract Migrations

This document records framework-owned migration notes for `POST /api/chat` and related reference-contract fields.

## Current Contract Version

- `1.0`

## Migration Log

### `1.0`

Baseline response envelope fields:

- `contract_version`
- `message`
- `citations`
- `collapsed_citations`
- `confidence`
- `answer`

Migration notes captured in this baseline:

1. Legacy evidence payloads may still expose `sources` instead of `citations`.
   The reference frontend keeps a compatibility fallback, but framework-owned producers should emit `citations` as the primary field.
2. Generation diagnostics now live under `message.generation`.
   Older consumers that only used `answer`, `confidence`, and `citations` remain compatible because the field is additive.
3. Citation shaping now follows generation-used evidence rather than the full retrieved set.
   Consumers should treat `citations` as the grounded answer support set, not as a retrieval dump.

## Update Rule

When a contract field is renamed, removed, or changes meaning:

- update `contract_version` in code;
- append a new migration entry here with the change, compatibility expectation, and consumer action;
- update [docs/reference-ui-contract.md](reference-ui-contract.md) in the same change set;
- add or update contract tests that prove the versioned behavior.