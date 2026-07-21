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
- expected_answer_terms: optional lexical terms expected in generated answer for correctness_proxy scoring
- expected_answer_contains: optional phrase(s) expected in generated answer for correctness_proxy scoring
- is_tabular_intent: whether tabular grounding policy should apply
- expected_tabular_terms: row/header terms expected in grounded tabular evidence
- expected_tabular_outcome: expected tabular result (`answer` for grounded row output, `abstain` when row-grounded answering should refuse)

These are framework-level starter rows and should be adapted to your corpus.

## Dataset sanity behavior in scripts/run_eval.py

The offline evaluator now performs row-level sanity checks when loading JSONL datasets.

- Rows with malformed JSON are reported as `invalid_json` and excluded from scoring.
- Rows that are not JSON objects are reported as `invalid_row_shape` and excluded.
- Rows missing a non-empty `query` are reported as `missing_query` and excluded.
- Optional expectation fields are normalized to string lists where possible and type issues are reported.

Sanity output is written to report JSON under `dataset_sanity` and summarized in report Markdown under `Dataset Sanity`, including a malformed-row preview table.
