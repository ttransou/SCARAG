# Profile Catalog

This document provides a compact map of the profile assets currently included in the repository and the purpose each one serves.

## Current placeholder profiles

The repository currently includes two placeholder profiles in the profiles/ directory:

### Default profile

- File: profiles/default.json
- Purpose: baseline profile for general-purpose schema-conscious RAG behavior.
- Use when: you want a neutral starting point before introducing domain-specific terminology or lifecycle rules.

### Humanities profile

- File: profiles/humanities.json
- Purpose: a humanities-oriented profile for archival, textual, and cultural heritage materials.
- Use when: your corpus contains provenance-heavy records, editions, oral histories, annotations, art-historical notes, or literary scholarship.

## Supporting assets

- File: config/humanities_doc_type_taxonomy.json
  - Adds humanities-specific document types such as archival_record, edition, oral_history, art_work, and literary_work.
- File: config/humanities_synonyms.json
  - Provides humanities-oriented vocabulary for provenance, attribution, archive, annotation, art, and literature.
- File: docs/humanities-profile.md
  - Documents the rationale, intended use, and design thinking behind the humanities profile.

## Profile creation pattern

A new profile typically consists of:

1. a profile overlay file in profiles/,
2. a taxonomy file in config/ for domain-specific document types,
3. a synonym file in config/ for domain vocabulary and query expansion,
4. and supporting documentation in docs/ that explains the rationale and intended application.

This pattern makes it easier for implementors to create domain-specific profiles without changing the framework core.
