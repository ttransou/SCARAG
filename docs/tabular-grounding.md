# SCARAG Tabular Grounding

This document defines row-grounded answering rules for tabular intent.

## Current Public Baseline
- tabular intent detection,
- abstention when tabular intent has no tabular evidence.

## Reconstruction Targets
- matched-row grounding behavior,
- header and row-window fidelity requirements,
- schema-style fallback policy controls,
- tabular-specific evaluation diagnostics.

## Safety Rule
When row-level evidence is insufficient, abstention is the correct behavior.
