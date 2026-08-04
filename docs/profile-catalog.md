# Profile Catalog

This document provides a compact map of the profile assets currently included in the repository and the purpose each one serves.

## Active branch profile

The active runtime profile for this branch is `shakespeare_test`.

### Shakespeare test profile

- File: profiles/shakespeare_test.json
- Purpose: default Shakespeare corpus profile for this branch, covering mixed-format works, source-work-aware retrieval, and Shakespeare-specific document typing.
- Use when: you are running the repository normally on this branch.

## Secondary comparison profiles

The repository still includes additional profiles in the profiles/ directory for comparison or framework-oriented testing:

### Default profile

- File: profiles/default.json
- Purpose: neutral baseline profile for framework-level regression checks.
- Use when: you want to compare Shakespeare behavior against an untailored baseline.

### Humanities profile

- File: profiles/humanities.json
- Purpose: broader humanities-oriented comparison profile for archival, textual, and cultural heritage materials.
- Use when: you are comparing the Shakespeare overlay against a more general humanities configuration.

## Supporting assets

- File: config/humanities_doc_type_taxonomy.json
  - Adds humanities-specific document types such as archival_record, edition, oral_history, art_work, and literary_work.
- File: config/humanities_synonyms.json
  - Provides humanities-oriented vocabulary for provenance, attribution, archive, annotation, art, and literature.
- File: docs/humanities-profile.md
  - Documents the rationale, intended use, and design thinking behind the humanities comparison profile.
- File: config/shakespeare_doc_type_taxonomy.json
  - Adds Shakespeare-specific work and genre typing for known corpus titles, source forms, and fallback behavior.
- File: config/shakespeare_synonyms.json
  - Provides Shakespeare-oriented vocabulary for dramatic structure, editorial context, and work-name retrieval.
- File: docs/shakespeare-test-profile.md
  - Documents the rationale, intended use, and operating assumptions behind the branch-default Shakespeare profile.

## Profile creation pattern

A new profile typically consists of:

1. a profile overlay file in profiles/,
2. a taxonomy file in config/ for domain-specific document types,
3. a synonym file in config/ for domain vocabulary and query expansion,
4. and supporting documentation in docs/ that explains the rationale and intended application.

This pattern makes it easier for implementors to create domain-specific profiles without changing the framework core.
