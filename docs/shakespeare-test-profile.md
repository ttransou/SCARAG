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

The profile prioritizes play, sonnet, edition, and primary-source style materials while reducing priority for generic table-like assets unless the query intent is explicitly tabular.

It also boosts terms associated with textual criticism and dramatic structure, such as folio, quarto, act, scene, and soliloquy.

## Profile structure

The profile is implemented through three coordinated assets:

- profile overlay: profiles/shakespeare_test.json
- taxonomy overlay: config/shakespeare_doc_type_taxonomy.json
- synonym set: config/shakespeare_synonyms.json

This composition keeps Shakespeare-specific behavior in branch-local overlays while preserving SCARAG framework core neutrality.
