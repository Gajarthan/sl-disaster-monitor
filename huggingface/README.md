---
pretty_name: Sri Lanka Disaster Monitor
language:
- en
- si
- ta
license: other
license_name: source-specific-terms
license_link: https://github.com/Gajarthan/sl-disaster-monitor/blob/main/DATA_LICENSE.md
task_categories:
- tabular-classification
tags:
- sri-lanka
- disasters
- weather
- dmc
configs:
- config_name: default
  data_files:
  - split: train
    path: data/alerts-*.parquet
---

# Sri Lanka Disaster Monitor

Independent, deterministic extraction from official [Disaster Management Centre, Sri Lanka](https://www.dmc.gov.lk/) report listings and linked PDFs. This is **not an official DMC service** and is not an emergency notification system. Follow the original report and local authorities.

## Contents and collection

Four categories: situation reports, weather forecasts/advisories, river water levels/flood warnings, and landslide warnings. The initial collection starts in September 2026 with a limited recent backfill; earlier dates may appear when a category's latest page includes older reports. This is not a complete DMC historical archive. Scheduled incremental updates run approximately every two hours via public GitHub Actions, subject to provider scheduling delays and source availability.

Yearly Zstandard-compressed Parquet files contain one record per SHA-256 PDF content hash. PDF files remain on DMC servers. The repository does not mirror PDFs. Original listing date/time are retained; issued_at interprets them as Sri Lanka time (+05:30). Missing time remains null rather than inventing midnight.

## Fields

`id`, `source`, `document_type`, `hazard`, `hazards`, `severity`, `title`, `description`, `summary`, `language`, `languages_detected`, `language_confidence`, `language_reason`, `issued_at`, `valid_from`, `valid_until`, `districts`, `provinces`, `source_page`, `source_pdf`, `content_hash`, `processed_at`.

`official_json` preserves source listing metadata. `extraction_json` records the extraction version, status, severity evidence, and interpretation limits. These nested objects are JSON strings in Parquet for stable Dataset Server access. `district_<name>` boolean columns support server-side district filtering without unsupported array predicates; e.g. `district_nuwara_eliya`.

`summary` is the first 600 characters of PDF-extracted text, not an AI summary. `description` is empty when the source listing has no description. Languages use page-level Unicode scripts and English word evidence. A bilingual PDF can have `language=mul` and `languages_detected=["en","si"]`; multiple languages within one page are also retained. `extraction_json.language_detection` records per-page classifications, evidence, heuristic confidence and version. Multilingual does not imply unreadable text or a need for OCR, and language presence does not guarantee a complete translation. Truly insufficient or unrecognized text has distinct reasons; OCR is not included. Boolean `language_en`, `language_si`, `language_ta` columns support Dataset Server membership filters for both single-language and multilingual records. Districts and provinces are **mentions**, not verified affected zones. Keywords may include background context, tables, or negation; hazard labels are discovery aids. Severity only normalizes explicit listing-title labels; all unsupported cases remain `unknown`. Validity is not inferred and stays null. Never interpret missing records as safety or all-clear.

## Querying

Use the public Dataset Server `/filter` endpoint with `dataset=gajarthan/sl-disaster-alerts`, `config=default`, `split=train`, and e.g. `where="district_jaffna"=true AND "hazard"='heavy_rain'`. The static dashboard reads current JSON from GitHub and remains usable during a Hub outage. Dataset Server indexing is asynchronous and can be unavailable or partial; inspect its response and do not treat failures as zero results.

## Rights and provenance

Source: Disaster Management Centre, Sri Lanka. Reports can originate from the Department of Meteorology, Department of Irrigation and NBRO and be republished by DMC. This dataset does not claim copyright over government source documents or grant rights that the original publishers have not granted. See the project DATA_LICENSE.md. No personal contact lists, credentials or PDF binaries are included.

[Source code, limitations and pipeline health](https://github.com/Gajarthan/sl-disaster-monitor) · [Dashboard](https://gajarthan.github.io/sl-disaster-monitor/)
