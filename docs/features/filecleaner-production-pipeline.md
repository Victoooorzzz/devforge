# FileCleaner Production Pipeline

## Scope

File Cleaner now has one production data-cleaning pipeline for CSV, Excel, and JSON files, plus the existing image/PDF metadata stripping utility. The data pipeline is async and job-based: upload raw file to R2, create a pending Neon record, process from the worker outbox, save a cleaned file and JSON report to R2, then mark the job completed or failed.

## Pipeline

1. Analyze file profile.
   - Detect encoding, delimiter, headers, columns, row count, and first 100 preview rows.
   - If detection fails, return manual options instead of crashing.

2. Create job.
   - Reject files over 100MB on Free/Pro.
   - Persist raw object key, config JSON, detection JSON, notification destinations, and status `pending`.

3. Worker processing.
   - Move status to `processing`.
   - Apply basic cleaning: null accounting, empty row removal, trim, text normalization, duplicate removal.
   - Apply normalization: countries to ISO, phones to E.164, currencies to numeric amount plus ISO code, dates to ISO 8601 UTC.
   - Run fuzzy_matching: Levenshtein, Jaro-Winkler style weighted score, and Token Set scoring with threshold.
   - Run schema_validation: int, float, email, date, regex, min/max, unique, enum, not null, and simulated cross-column foreign key.
   - Run anomaly_detection: numeric z-score/IQR/MAD outliers, categorical cardinality, null clusters, and format inconsistencies.

4. Persist outputs.
   - Upload cleaned file to `cleaned/{id}_{filename}`.
   - Upload report JSON to `reports/{id}.json`.
   - Store report JSON and output keys on `processed_files`.

5. Retry and terminal state.
   - Failed jobs retry two times through the outbox.
   - After two retries, status becomes `failed` with `Manual review required`.
   - User cancellation sets `canceled` and deletes temp raw/clean/report objects.

6. Notifications.
   - Optional email notification via Resend.
   - Optional webhook notification only to public http(s) URLs to avoid SSRF.

## Frontend Surface

The dashboard should continue exposing:

- `/files/analyze` preview.
- `/files/upload` with `config_json`.
- `/files/{id}/status` polling.
- `/files/{id}/report` report details.
- `/files/{id}/cancel` cancellation.
- `/files/utility` metadata stripping and image/PDF conversion.

## CLI Surface

The CLI should support analyze, upload, status, report, cancel, and download commands against the same backend endpoints.
