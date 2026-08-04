# Configuration samples

This directory holds sample JSON configuration files for the repository.

These files are meant to be adapted to your domain and deployment rather than treated as fixed, one-size-fits-all schemas. The JSON format does not support comments, so human-readable notes are provided through descriptive keys such as `schema_note` where appropriate.

Current examples:
- `synonyms.json`: sample thesaurus and intent-group structure for query expansion and tabular intent handling.

## Optional legacy DOC helpers

Legacy `.doc` extraction quality can vary significantly across corpora. The framework includes a built-in fallback parser, but helper tools improve extraction for many Word 97-2003 documents.

Recommended helpers on Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y antiword catdoc
```

Why this is recommended:
- improves text fidelity for old `.doc` assets used in ingestion regression suites,
- reduces binary-noise artifacts that can skew doc-type inference,
- keeps parser selection explicit in ingestion diagnostics (`doc_legacy_antiword_parser` or `doc_legacy_catdoc_parser`).

Fallback behavior remains available when helpers are not installed.
