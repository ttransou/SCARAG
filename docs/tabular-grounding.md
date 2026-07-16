# SCARAG Tabular Grounding

This document defines row-grounded answering rules for tabular intent.

## Current Public Baseline
- tabular intent detection,
- strict row-grounded tabular policy: tabular intent answers must be backed by matched table rows,
- abstention when tabular intent has no matched row evidence,
- tabular trace output with matched chunk and row counts.
- spreadsheet ingestion now preserves sheet-local table boundaries and row offsets so XLSX/XLS row windows remain traceable through chunking.

## Roadmap Targets
- header and row-window fidelity requirements,
- schema-style fallback policy controls,
- tabular-specific evaluation diagnostics.

## Schema-Style Fallback Policy

Schema-style fallback is a narrow exception, not a general escape hatch.

Baseline guardrails:

- allow schema-style fallback only for structure-seeking tabular queries, such as requests for headers, columns, sheet names, or whether a table contains a field;
- do not use schema-style fallback for value claims, row comparisons, totals, rankings, or entity-specific assertions;
- if the query asks for row-level facts and no matched rows survive grounding, abstain instead of synthesizing from headers alone;
- when schema fallback is used, cite only the table structure that was actually observed and avoid implying row-level confirmation.

Allowed baseline outputs:

- header names or column labels,
- sheet or table identifiers when explicitly available,
- a statement that a table shape exists but does not support a row-grounded answer.

Disallowed baseline outputs:

- inferred values from unlabeled columns,
- aggregates reconstructed from partial rows,
- entity-specific answers supported only by table schema.

## PDF Table Behavior And Limits

PDF tables are permitted for grounded tabular answers only when extraction preserves usable row and header structure.

Baseline limits:

- treat PDF table extraction as conditionally row-groundable, not automatically trusted;
- require observable row text plus stable header/value alignment before using PDF table evidence for row-grounded answers;
- if extraction collapses columns, merges rows ambiguously, or loses enough structure that matched rows are no longer inspectable, abstain;
- do not use PDF table structure alone to justify schema-style fallback for row-value questions.

Operational consequence:

- PDF-derived table evidence may support grounded answers when rows remain reviewable in chunk text;
- otherwise the correct framework behavior is abstention with preserved provenance, not best-effort reconstruction.

## Evaluation Diagnostics

The offline evaluator now distinguishes between:

- tabular answer success, where a tabular-intent sample is expected to produce grounded rows and does so;
- tabular abstention correctness, where a tabular-intent sample is expected to refuse and does so;
- tabular row-term matching, which confirms that expected row/header terms appear in grounded evidence.

## Safety Rule
When row-level evidence is insufficient, abstention is the correct behavior.
