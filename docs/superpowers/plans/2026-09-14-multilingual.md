# Multilingual PDF language fix

User-authorized scope: detect multiple languages in a PDF, keeping mixed language distinct from unsupported/unreadable text. Preserve existing official metadata, IDs, hazard and location fields during archive migration.

- [x] Add regression tests for bilingual pages, three scripts on one page, short headings, blank/unsupported text, real PDF page separators, schema/list agreement, Parquet roundtrip and legacy records.
- [x] Preserve PDF page boundaries and implement versioned per-page evidence; add languages_detected and the mul label.
- [x] Add scalar language membership columns for historical filtering and an idempotent, hash-checked archive language migration.
- [x] Reprocess all existing records and inspect corrected real advisory examples.
- [x] Update dashboard cards, details, local/Hugging Face filters and documentation.
- [ ] Validate, publish dataset/code, and verify hosted filters and successful workflows.

Validation: Python and Node test suites, compare pre/post archive fields, local/hosted browser checks, public Parquet readback and GitHub Actions outcomes. Do not conflate fewer unknown labels with a measured accuracy score.
