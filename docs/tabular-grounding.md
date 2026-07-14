# SCARAG Tabular Grounding

This document defines row-grounded answering rules for tabular intent.

## Current Public Baseline
- tabular intent detection,
- strict row-grounded tabular policy: tabular intent answers must be backed by matched table rows,
- abstention when tabular intent has no matched row evidence,
- tabular trace output with matched chunk and row counts.

## Roadmap Targets
- header and row-window fidelity requirements,
- schema-style fallback policy controls,
- tabular-specific evaluation diagnostics.

## Safety Rule
When row-level evidence is insufficient, abstention is the correct behavior.
