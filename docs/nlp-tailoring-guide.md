# NLP Tailoring Guide

The humanities profile is an example of how SCARAG can be tailored for a domain with distinctive evidence practices.

1. Define domain vocabulary and synonyms.
   - For humanities work, this may include terms related to provenance, attribution, edition, repository context, annotation, iconography, or textual transmission.
   - Controlled vocabularies such as ULAN or the Getty AAT can be used as references for vocabulary normalization and query expansion.
2. Identify boilerplate patterns and lifecycle signals.
   - In cultural heritage or archival settings, repeated boilerplate may be less central than source provenance, editorial status, or review history.
   - Lifecycle signals may reflect review state, curation status, or the maturity of a catalog or transcription.
3. Tune chunking and retrieval heuristics on representative documents.
   - A humanities corpus may include notebooks, catalog entries, archival descriptions, oral histories, and scholarly notes that require different retrieval behavior from generic policy or support collections.
   - Profile-level retrieval overlays can support this by changing preferred document types and boosting provenance-related terms.
4. Validate behavior with offline eval datasets.
   - Evaluate whether the profile improves retrieval of relevant evidence, whether provenance-heavy documents are surfaced appropriately, and whether the system abstains or underperforms when evidence is weak.
   - Use the same process for other implementors who want to build profiles outside the humanities domain.
