# Shakespeare test profile

This profile is the branch scope for Shakespeare-only testing and is not intended as a generic cross-domain profile.

The branch workflow uses baseline humanities overlays as a foundation, then generates candidate metadata in preparation for ingestion of Shakespeare works.

## Why this profile exists

The Shakespeare test profile separates branch experimentation from framework core behavior while keeping the branch objective explicit: test Shakespeare-specific retrieval and metadata behavior before ingestion commits are finalized.

It is designed for corpora with different publication and transcription forms of the same underlying works, where retrieval quality depends on recognizing play-level signals, edition context, and textual criticism vocabulary.

## Intended use

- mixed-format Shakespeare corpora (txt, md, pdf, docx, html, xml)
- corpora that blend source-text excerpts, editorial apparatus, and commentary
- evaluations where source naming conventions (for example Hamlet, Macbeth, or Sonnet labels) should influence document typing
- metadata generation passes that create candidate fields for ingestion review (for example provisional doc_type, source-unit cues, and terminology normalization hints)

## Operating constraint

This branch should contain Shakespeare test assets only. Domain-general experimentation belongs in framework or separate implementation branches.

## Retrieval emphasis

For this branch test cycle, Shakespeare corpora are differentiated into genre-aware play classes (`play_tragedy`, `play_comedy`, `play_history`) and `sonnet` where source cues are explicit, with `primary_source` as the fallback class.

This profile intentionally excludes `policy`/`procedure` drift by preferring source-based overrides and extension defaults before content-pattern heuristics.

The profile still boosts terms associated with textual criticism and dramatic structure, such as folio, quarto, act, scene, and soliloquy.

## Corpus inventory and work mapping

Current Shakespeare test corpus files and their intended taxonomy mapping:

| Work | File | Format | Expected doc_type |
|---|---|---|---|
| Much Ado About Nothing | `data/Ado.xml` | XML | `play_comedy` |
| Shakespeare Sonnets (selection) | `data/Son.xml` | XML | `sonnet` |
| Hamlet | `data/hamlet_PDF_FolgerShakespeare.pdf` | PDF | `play_tragedy` |
| Othello | `data/othello_TXT_FolgerShakespeare.txt` | TXT | `play_tragedy` |
| Romeo and Juliet | `data/romeo-and-juliet_DOC-LN_FolgerShakespeare.doc` | DOC (legacy) | `play_tragedy` |
| The Taming of the Shrew | `data/the-taming-of-the-shrew_DOC-LN_FolgerShakespeare.doc` | DOC (legacy) | `play_comedy` |
| Titus Andronicus | `data/titus-andronicus_TXT_FolgerShakespeare.txt` | TXT | `play_tragedy` |

Genre mapping is handled in `config/shakespeare_doc_type_taxonomy.json` through source-name overrides first, then extension defaults, then content patterns, with `primary_source` as fallback.

This precedence order keeps classification stable for known works and avoids policy/procedure drift.

## Chunking strategy (SCARAG-grounded)

The chunking policy here follows SCARAG pipeline behavior in `scarag/pipeline.py` and is intentionally conservative for dramatic and poetic text.

Current operational settings (from `RagConfig`):

- `chunk_size = 120` words
- `overlap = 20` words
- `min_chunk_words = 40`
- `cohesion_threshold = 0.0`
- `table_chunk_rows = 25`
- `table_overlap_rows = 5`

### Prose chunking behavior

- Text is segmented into prose source units by paragraph boundaries.
- With `cohesion_threshold = 0.0`, SCARAG does not force semantic sentence splitting, which helps preserve verse/dialogue continuity.
- Sliding windows are applied at 120 words with 20-word overlap.
- Trailing windows below `min_chunk_words` are merged into the previous chunk, reducing tiny tail fragments.

### Tabular behavior

- SCARAG detects tabular structure via delimiter profile checks and explicit table metadata when present.
- For this Shakespeare corpus, current ingestion diagnostics report prose-only chunks (`total_tabular_chunks = 0`), so tabular row-window policy is currently inactive but kept available for future mixed corpora.

## Chunking fit validation for this corpus

Latest ingestion diagnostics (Shakespeare test profile):

- loaded files: 7
- total chunks: 3625
- prose chunks: 3625
- tabular chunks: 0

Per-work chunk counts from the latest validation run:

- `data/Ado.xml`: 308
- `data/Son.xml`: 221
- `data/hamlet_PDF_FolgerShakespeare.pdf`: 445
- `data/othello_TXT_FolgerShakespeare.txt`: 1296
- `data/romeo-and-juliet_DOC-LN_FolgerShakespeare.doc`: 372
- `data/the-taming-of-the-shrew_DOC-LN_FolgerShakespeare.doc`: 320
- `data/titus-andronicus_TXT_FolgerShakespeare.txt`: 663

Observed prose chunk-word distribution in this corpus:

- mean: 61.37
- median: 44
- max: 159
- very small chunks (<= 5 words): 12.17%
- one-word chunks: 0.08%

Interpretation:

- The overlap policy is preserving local dramatic context while keeping chunk bodies compact enough for retrieval.
- Median chunk length near the minimum threshold aligns with verse/dialogue-heavy structure and is acceptable for this branch objective.
- One-word fragments are negligible; no immediate chunk policy change is required.

If retrieval noise increases as corpus size grows, the first tuning lever should be a modest increase to `min_chunk_words` (for example 50) before changing overlap.

## Source metadata and named-work retrieval

To improve evidence distinction between works with overlapping themes, chunk metadata now carries explicit source identity fields:

- `source_work_key` (normalized work identifier from filename)
- `source_work_title` (human-readable work label)
- `source_work_tokens` (tokenized work label for matching)
- `source_format` (file extension without leading dot)

Retrieval scoring now includes a `source_work_boost` factor when query terms contain a named work token that matches chunk source-work metadata.

Validated behavior for this corpus:

- Query mentioning Hamlet returns Hamlet evidence at top rank.
- Query mentioning Othello returns Othello evidence at top rank.
- Score diagnostics include `source_work_boost` in component output.

## Acceptance checklist (quick run)

Use this checklist after each ingest/refresh cycle.

- Diagnostics contract: `diagnostics.contract_version == "1.0"`.
- Corpus load count: `loaded_files == 7` (or expected count when corpus intentionally changes).
- Unsupported formats: `unsupported_files == 0`.
- Internal artifacts only: skipped files are limited to SCARAG internal lifecycle artifacts.
- Genre typing present: at least one chunk each for `play_tragedy`, `play_comedy`, and `sonnet`.
- Drift guard: zero chunks inferred as `policy` or `procedure`.
- Parser quality: legacy DOC files report helper parser (`doc_legacy_antiword_parser` or `doc_legacy_catdoc_parser`) when helpers are installed.
- Chunking mode: `total_tabular_chunks == 0` for the current Shakespeare corpus snapshot.
- Sanity tests: ingestion-focused subset passes (`tests/test_ingestion_regression_mixed_formats.py`, `tests/test_ingestion_diagnostics_contract.py`, `tests/test_dependency_metadata.py`).

## Profile structure

The profile is implemented through three coordinated assets:

- profile overlay: profiles/shakespeare_test.json
- taxonomy overlay: config/shakespeare_doc_type_taxonomy.json
- synonym set: config/shakespeare_synonyms.json

This composition keeps Shakespeare-specific behavior in branch-local overlays while preserving SCARAG framework core neutrality.

## Legacy DOC ingestion note

Shakespeare corpora in this branch include legacy `.doc` files. To improve extraction fidelity, install helper tools before ingestion runs:

Branch-specific setup file:

- [requirements.shakespeare_test.txt](requirements.shakespeare_test.txt)

Install Python dependencies for this branch:

```bash
/home/codespace/.python/current/bin/python -m pip install -r requirements.shakespeare_test.txt
```

```bash
sudo apt-get update
sudo apt-get install -y antiword catdoc
```

Justification:
- legacy `.doc` fallback parsing can include binary-like noise tokens,
- helper extractors generally preserve cleaner title/body text,
- cleaner extraction improves candidate `doc_type` inference quality and reduces downstream brittleness.

When helpers are available, ingestion diagnostics should reflect helper parser paths for selected files.
