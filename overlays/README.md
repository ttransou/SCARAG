# Work-level context overlays

Each ingested work can have a manual YAML overlay in this directory.

## Naming convention

- Use the work stem from the source file as the filename.
- Examples:
  - `Ado.yaml` for `data/Ado.xml`
  - `othello_TXT_FolgerShakespeare.yaml` for `data/othello_TXT_FolgerShakespeare.txt`
  - `hamlet_PDF_FolgerShakespeare.yaml` for `data/hamlet_PDF_FolgerShakespeare.pdf`

## Structure

Each overlay should contain:

```yaml
metadata_tiers:
  context:
    composition_date: ""
    publication_or_performance_date: ""
    genre: []
    historical_setting: ""
    alternate_titles: []
    edition_history: []
    related_works: []
curation:
  curated_by: ""
  curated_at: "YYYY-MM-DD"
  source_note: ""
  review_status: draft
  confidence: medium
```

## Guidance for future overlays

- Keep the content work-level and document-scoped.
- Prefer concise factual values over interpretive claims.
- Use `review_status` to track whether the overlay is draft, reviewed, approved, or rejected.
- Keep `source_note` explicit so the provenance is visible to later reviewers.
- If a value is uncertain, leave it blank or use a lower confidence rather than guessing.
