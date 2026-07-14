# Evaluation Dataset Seeds

This folder now contains starter JSONL datasets for SCARAG evaluation layers:

- canonical.jsonl
- regression.jsonl
- drift.jsonl

Each row may include:

- id: stable sample identifier
- query: input question
- expected_sources: source substrings that should appear in retrieved evidence
- expected_confidence: expected confidence label (high, low, abstain)
- excluded_sources: source substrings that must not appear in retrieved evidence
- is_tabular_intent: whether tabular grounding policy should apply
- expected_tabular_terms: row/header terms expected in grounded tabular evidence

These are framework-level starter rows and should be adapted to your corpus.
