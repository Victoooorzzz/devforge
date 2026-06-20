# FileCleaner Frontend Contract

This contract covers the production File Cleaner flow for the dashboard, API clients, and CLI. It keeps the CSV/Excel/JSON data-cleaning pipeline and the existing image/PDF metadata stripping utility as separate product surfaces.

## Endpoints

- `POST /files/analyze`
  - Multipart field: `file`.
  - Returns file detection, `preview` for the first 100 rows, `encoding`, `delimiter`, `headers_detected`, `columns`, `row_count`, and `manual_options` when detection fails.

- `POST /files/upload`
  - Multipart fields: `file`, `config_json`, optional `notify_email`, optional `notify_webhook_url`.
  - Rejects files over 100MB for Free/Pro with HTTP 413.
  - Creates a pending job, stores the raw file in R2, persists detection/config in Neon, and enqueues the worker job.

- `GET /files/{id}/status`
  - Returns `pending`, `processing`, `completed`, `failed`, or `canceled`.
  - Includes `download_url`, `report_url`, `detection`, and `report` when available.

- `GET /files/{id}/report`
  - Returns the persisted JSON report with `basic_cleaning`, `fuzzy_matching`, `schema_validation`, `anomaly_detection`, `normalization`, and `detection`.

- `POST /files/{id}/cancel`
  - Cancels a non-completed job and cleans raw/clean/report temp objects from R2.
  - Frontend action template: `/files/{fileId}/cancel`.

- `GET /files/{id}/download`
  - Redirects to the cleaned file in R2.

- `POST /files/utility`
  - Existing metadata stripping, image compression, image conversion, SVG conversion, HEIC conversion, and PDF page export utility.
  - This is not a replacement for CSV cleaning; keep it visible as "Clean image or PDF".

## `config_json`

```json
{
  "basic_cleaning": {
    "drop_empty_rows": true,
    "trim_whitespace": true,
    "normalize_text": true,
    "drop_duplicates": true
  },
  "fuzzy_matching": {
    "enabled": true,
    "columns": ["company", "name"],
    "threshold": 85
  },
  "schema_validation": {
    "rules": [
      {"column": "email", "type": "email", "not_null": true},
      {"column": "amount", "type": "float", "min": 0},
      {"column": "country", "type": "string", "enum": ["US", "PE"]}
    ]
  },
  "anomaly_detection": {
    "enabled": true,
    "numeric_columns": ["amount"],
    "categorical_columns": ["country"]
  },
  "normalization": {
    "countries": ["country"],
    "phones": [{"column": "phone", "default_country_code": "+1"}],
    "currencies": ["amount"],
    "dates": ["created_at"]
  }
}
```

## Report Keys

- `basic_cleaning`: rows original/clean, duplicates removed, empty rows removed, whitespace fixes, null cell counts.
- `fuzzy_matching`: clusters by column, representative value, affected rows, algorithms.
- `schema_validation`: valid/invalid row counts and per-column errors.
- `anomaly_detection`: numeric outlier, null cluster, cardinality, and format inconsistency flags.
- `normalization`: ISO countries, E.164 phones, numeric currency amount plus currency code, ISO 8601 UTC dates.

## Frontend Requirements

- Show "Preview first 100 rows" after `/files/analyze`.
- Expose controls for Fuzzy matching, Schema validation, Anomaly detection, and Normalization before upload.
- Upload the selected `config_json` to `/files/upload`.
- Poll `/files/{id}/status` until terminal state.
- Allow cancel through `/files/{id}/cancel` while status is `pending` or `processing`.
- Show report metrics for fuzzy clusters, schema invalid rows, anomaly flags, and normalization edits.
- Keep metadata stripping utility available for images/PDFs.
