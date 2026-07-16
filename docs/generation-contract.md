# SCARAG Grounded Answer Contract

This document defines the baseline answer-generation contract for SCARAG.

## Purpose

Generation is allowed to present evidence. It is not allowed to outrun evidence.

The baseline contract exists to keep answer text, abstention behavior, and citations aligned with the evidence that actually supported the output.

## Allowed Synthesis Boundaries

Baseline generation may:

- reproduce or lightly compress retrieved text snippets;
- present up to a small number of directly matched tabular rows for tabular intent;
- omit repeated boilerplate when doing so does not change factual meaning;
- abstain when retained evidence does not support a grounded claim.

Baseline generation may not:

- infer unsupported facts across multiple weak snippets;
- resolve contradictory evidence silently;
- produce row-value claims from table schema alone;
- cite evidence that was retrieved but not actually used in the answer text.

## Citation Obligations

The generator must identify which evidence units were actually used.

Baseline citation obligations:

- the API citation set should be shaped from the generator's cited chunk ids, not the full retrieval set;
- citations must preserve provenance and citation-quality checks before emission;
- if the generator abstains because no grounded claim can be made, the citation set may be empty;
- if the generator uses tabular rows, citations should point to the chunks that contained those matched rows.

## Abstention Policy Taxonomy

Baseline abstention and placeholder reason codes:

- `no_supporting_evidence`: no retained evidence reached generation;
- `usable_evidence_missing`: retained evidence existed but offered no usable extractive text;
- `tabular_row_evidence_missing`: tabular intent lacked matched row evidence;
- `live_adapter_unconfigured`: live generation mode was selected but no implementation adapter exists in framework baseline.

These reason codes are framework diagnostics. Implementations may layer richer taxonomies on top, but should keep a stable mapping for these baseline cases.

## Contract Consequences

- answer text and citations should move together;
- abstention is a valid grounded output, not an error state;
- confidence remains a separate signal and should not be treated as a substitute for abstention reason codes.