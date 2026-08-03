# Humanities profile

This profile is tuned for archival, textual, and art-historical materials where provenance, interpretation, and authority control matter.

## Why this profile exists

The humanities profile exists to make SCARAG useful for domains where documents are not merely informational artifacts but cultural, interpretive, and evidentiary objects. In practice, that means a user may need to retrieve material that is shaped by authorship, attribution, edition history, translation, repository context, or scholarly annotation.

A humanities-oriented RAG workflow should therefore be more explicit about provenance and interpretation than a generic baseline profile. The goal is not to impose a single scholarly method on every collection, but to provide a starting point that reflects the kinds of evidence humanities researchers and cultural heritage workers routinely rely on.

## Intended use

- archives and finding aids
- critical editions and translations
- oral histories and interview transcripts
- annotations, commentary, and research notes
- art historical catalog entries, iconography, and museum documentation
- literary analysis and textual studies

## Authority references

The profile is designed to work alongside controlled vocabularies and authority files used in cultural heritage practice, especially:

- Getty Research Institute: Union List of Artist Names (ULAN)
- Getty Art & Architecture Thesaurus (AAT)

## Retrieval emphasis

The profile favors note-like documents and provenance-heavy materials, while lowering confidence for stale or lightly documented records. It also gives extra weight to documents whose content explicitly indicates provenance, attribution, edition history, or scholarly interpretation.

## Profile structure

The humanities profile is implemented through three coordinated assets:

- a profile overlay in profiles/humanities.json
- a humanities-specific document-type taxonomy in config/humanities_doc_type_taxonomy.json
- a humanities-oriented synonym set in config/humanities_synonyms.json

These files are intended to be adapted as a domain implementor learns more about a specific collection, institution, or research workflow.
