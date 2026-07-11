import asyncio
import io
import json
import sys
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from fastapi.testclient import TestClient
import fitz

import apps.filecleaner.backend.main as file_main
from apps.filecleaner.backend.main import ProcessedFile
from backend_core.auth import User, get_current_user
from backend_core.database import get_session
from backend_core.plan_limits import FILECLEANER_LIMITS


def _trial_user(user_id=42):
    return User(
        id=user_id,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


class _FakeSession:
    def __init__(self, record=None):
        self.record = record
        self.added = []
        self.deleted = []
        self.commits = 0

    async def get(self, _model, _id):
        return self.record

    async def execute(self, _query):
        raise AssertionError("Unexpected query")

    def add(self, item):
        self.added.append(item)
        if getattr(item, "id", None) is None:
            item.id = len(self.added)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = len(self.added) or 1

    async def delete(self, item):
        self.deleted.append(item)


class _FakeS3:
    def __init__(self, raw=b""):
        self.raw = raw
        self.uploads = {}
        self.deleted = []

    def upload_fileobj(self, fileobj, bucket, key):
        self.uploads[(bucket, key)] = fileobj.read()

    def download_fileobj(self, _bucket, _key, fileobj):
        fileobj.write(self.raw)

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))

    def generate_presigned_url(self, *_args, **_kwargs):
        return "https://storage.example.test/download"


def _client(session):
    file_main.app.dependency_overrides.clear()
    file_main.app.dependency_overrides[get_current_user] = lambda: _trial_user()

    async def override_session():
        yield session

    file_main.app.dependency_overrides[get_session] = override_session
    return TestClient(file_main.app)


class FileCleanerProductionPipelineTests(unittest.TestCase):
    def tearDown(self):
        file_main.app.dependency_overrides.clear()

    def test_detects_encoding_delimiter_headers_and_preview_first_100_rows(self):
        rows = ["name;email;amount"]
        rows.extend(f"Customer {i};customer{i}@example.test;{i}" for i in range(120))
        content = "\n".join(rows).encode("utf-8")

        profile = file_main.detect_file_profile(content, "customers.csv")

        self.assertTrue(profile["loadable"])
        self.assertEqual(profile["encoding"], "utf-8")
        self.assertEqual(profile["delimiter"], ";")
        self.assertTrue(profile["headers_detected"])
        self.assertEqual(profile["columns"], ["name", "email", "amount"])
        self.assertEqual(profile["preview_row_count"], 100)
        self.assertEqual(profile["preview"][0]["name"], "Customer 0")

    def test_unreadable_profile_returns_manual_options_instead_of_crashing(self):
        profile = file_main.detect_file_profile(b"\x00\x01\x02\x03\xff\x00", "broken.csv")

        self.assertFalse(profile["loadable"])
        self.assertIn("manual_options", profile)
        self.assertIn("encoding", profile["manual_options"])
        self.assertIn("delimiter", profile["manual_options"])

    def test_runs_full_configurable_pipeline_and_persists_report_shape(self):
        content = (
            "company,email,amount,country,phone,joined_at,category\n"
            " Acme Inc ,Ops@Example.COM,$10.00,United States,(415) 555-0100,01/02/2026,core\n"
            "\"Acme, Inc.\",bad-email,$9999.00,USA,415-555-0101,not-a-date,core\n"
            "Globex,,USD 12.00,Peru,987654321,2026-03-04,rare-unique\n"
            ",,,,,,\n"
            "Globex,,USD 12.00,Peru,987654321,2026-03-04,rare-unique\n"
        ).encode("utf-8")
        config = {
            "basic_cleaning": {
                "drop_empty_rows": True,
                "trim_whitespace": True,
                "normalize_text": True,
                "drop_duplicates": True,
            },
            "fuzzy_matching": {
                "enabled": True,
                "columns": ["company"],
                "threshold": 80,
            },
            "schema_validation": {
                "rules": [
                    {"column": "email", "type": "email", "not_null": True},
                    {"column": "amount", "type": "float", "min": 0},
                    {"column": "country", "type": "string", "enum": ["US", "PE"]},
                ]
            },
            "anomaly_detection": {
                "enabled": True,
                "numeric_columns": ["amount"],
                "categorical_columns": ["category"],
            },
            "normalization": {
                "countries": ["country"],
                "phones": [{"column": "phone", "default_country_code": "+1"}],
                "currencies": ["amount"],
                "dates": ["joined_at"],
            },
        }

        result = file_main.run_filecleaner_pipeline(content, "customers.csv", config)

        self.assertEqual(result.report["basic_cleaning"]["rows_original"], 5)
        self.assertEqual(result.report["basic_cleaning"]["empty_removed"], 1)
        self.assertEqual(result.report["basic_cleaning"]["duplicates_removed"], 1)
        self.assertEqual(result.report["basic_cleaning"]["rows_clean"], 3)
        self.assertGreaterEqual(result.report["fuzzy_matching"]["clusters_found"], 1)
        self.assertGreater(result.report["schema_validation"]["invalid_rows"], 0)
        self.assertGreater(result.report["schema_validation"]["columns"]["email"]["invalid_count"], 0)
        self.assertGreaterEqual(result.report["anomaly_detection"]["total_flags"], 1)
        self.assertEqual(set(result.dataframe["country"].dropna().tolist()), {"US", "PE"})
        self.assertTrue(result.dataframe["phone"].dropna().iloc[0].startswith("+1"))
        self.assertTrue(result.dataframe["joined_at"].dropna().iloc[0].endswith("Z"))
        self.assertIn("amount_currency", result.dataframe.columns)
        self.assertEqual(result.report["normalization"]["countries_normalized"], 3)

    def test_basic_clean_trims_text_values_in_non_object_columns_without_stringifying_numbers(self):
        df = file_main.pd.DataFrame({
            "sku": file_main.pd.Series([" 001 ", " 002 "], dtype="category"),
            "amount": file_main.pd.Series([1000, 2000], dtype="int64"),
        })

        cleaned, report = file_main._basic_clean(df, {
            "drop_empty_rows": True,
            "trim_whitespace": True,
            "normalize_text": True,
            "drop_duplicates": True,
        })

        self.assertEqual(cleaned["sku"].astype(str).tolist(), ["001", "002"])
        self.assertEqual(cleaned["amount"].tolist(), [1000, 2000])
        self.assertEqual(str(cleaned["amount"].dtype), "int64")
        self.assertEqual(report["whitespace_fixed"], 2)

    def test_currency_parser_handles_peruvian_and_european_thousands(self):
        self.assertEqual(file_main._parse_currency("S/ 1,500"), (1500.0, "PEN"))
        self.assertEqual(file_main._parse_currency("1.234,56 \u20ac"), (1234.56, "EUR"))
        self.assertEqual(file_main._magic_clean_price("$1,500.25"), 1500.25)

    def test_deep_clean_detects_semantics_and_reports_business_fixes(self):
        content = (
            "Nombre,Correo,Telefono,Pais,DNI,credit_score,monto,fecha_nacimiento,fecha_contratacion\n"
            " ana lopez ,ana dot lopez at example dot com,987654321,Peru,12345678,720,\"S/ 1,500.50\",1990-01-01,2024-02-01\n"
            "Bob Smith,bob@example.com,(415) 555-0100,usa,20123456789,920,\"$2,000.00\",2010-01-01,2020-01-01\n"
        ).encode("utf-8")

        result = file_main.run_deep_clean(content, "customers.csv")

        self.assertEqual(result.report["version"], "filecleaner-deepclean-v6")
        self.assertEqual(result.report["deep_clean"]["columns_detected"]["Correo"], "email")
        self.assertEqual(result.report["deep_clean"]["columns_detected"]["Pais"], "country")
        self.assertEqual(result.dataframe["Correo"].iloc[0], "ana.lopez@example.com")
        self.assertEqual(result.dataframe["Pais"].tolist(), ["PE", "US"])
        self.assertEqual(result.dataframe["DNI"].iloc[0], "DNI-12345678")
        self.assertTrue(file_main.pd.isna(result.dataframe["credit_score"].iloc[1]))
        self.assertTrue(result.report["deep_clean"]["warnings"])

    def test_deep_clean_endpoint_is_pro_only(self):
        async def free_limits(_user, _session):
            return "free", FILECLEANER_LIMITS["free"]

        with patch.object(file_main, "get_filecleaner_limits", free_limits):
            response = _client(_FakeSession()).post(
                "/files/deep-clean",
                files={"file": ("customers.csv", b"name,email\nAna,ana@example.test\n", "text/csv")},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Pro", response.json()["detail"])

    def test_pdf_utility_returns_multipage_pdf_and_persists_files_to_r2(self):
        document = fitz.open()
        document.set_metadata({"author": "Private Author", "title": "Private Report"})
        for page_number in range(1, 3):
            page = document.new_page(width=240, height=160)
            page.insert_text((24, 80), f"Page {page_number}")
        source_pdf = document.tobytes()
        document.close()

        fake_s3 = _FakeS3()
        session = _FakeSession()

        async def pro_limits(_user, _session):
            return "pro", FILECLEANER_LIMITS["pro"]

        with patch.object(file_main.settings, "s3_bucket_name", "filecleaner-files"), \
             patch.object(file_main, "_get_s3_client", lambda: fake_s3), \
             patch.object(file_main, "get_filecleaner_limits", pro_limits):
            response = _client(session).post(
                "/files/utility",
                files={"file": ("brief.pdf", source_pdf, "application/pdf")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(
            response.headers["content-disposition"],
            'attachment; filename="brief.cleaned.pdf"',
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

        cleaned = fitz.open(stream=response.content, filetype="pdf")
        self.assertEqual(cleaned.page_count, 2)
        self.assertEqual(cleaned.metadata.get("author"), "")
        self.assertEqual(cleaned.metadata.get("title"), "")
        cleaned.close()

        self.assertEqual(
            fake_s3.uploads[("filecleaner-files", "raw/1_brief.pdf")],
            source_pdf,
        )
        self.assertEqual(
            fake_s3.uploads[("filecleaner-files", "cleaned/1_brief.cleaned.pdf")],
            response.content,
        )
        record = next(item for item in session.added if isinstance(item, ProcessedFile))
        self.assertEqual(record.status, "completed")
        self.assertEqual(record.raw_object_key, "raw/1_brief.pdf")
        self.assertEqual(record.cleaned_object_key, "cleaned/1_brief.cleaned.pdf")

    def test_schema_regex_requires_full_value_match(self):
        df = file_main.pd.DataFrame({"code": ["123", "123abc"]})
        report = file_main._run_schema_validation(
            df,
            {"rules": [{"column": "code", "type": "regex", "pattern": r"\d+"}]},
        )

        self.assertEqual(report["invalid_rows"], 1)
        self.assertEqual(report["columns"]["code"]["errors"][0]["row_index"], 1)

    def test_upload_rejects_free_files_over_plan_limit(self):
        oversized_free_file = b"0" * (10 * 1024 * 1024 + 1)
        response = _client(_FakeSession()).post(
            "/files/upload",
            files={"file": ("large.csv", oversized_free_file, "text/csv")},
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("10MB", response.json()["detail"])

    def test_cancel_pending_job_marks_canceled_and_deletes_temp_objects(self):
        record = ProcessedFile(
            id=7,
            user_id=42,
            original_name="customers.csv",
            size_bytes=100,
            status="pending",
            raw_object_key="raw/7_customers.csv",
            cleaned_object_key="cleaned/7_customers.csv",
            report_object_key="reports/7.json",
        )
        fake_s3 = _FakeS3()

        with patch.object(file_main.settings, "s3_bucket_name", "bucket"), patch.object(file_main, "_get_s3_client", lambda: fake_s3):
            response = _client(_FakeSession(record)).post("/files/7/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(record.status, "canceled")
        self.assertIn(("bucket", "raw/7_customers.csv"), fake_s3.deleted)
        self.assertIn(("bucket", "cleaned/7_customers.csv"), fake_s3.deleted)
        self.assertIn(("bucket", "reports/7.json"), fake_s3.deleted)

    def test_failed_job_retries_twice_then_marks_failed(self):
        record = ProcessedFile(
            id=8,
            user_id=42,
            original_name="broken.csv",
            size_bytes=10,
            status="pending",
            retry_count=0,
        )
        session = _FakeSession(record)
        fake_s3 = _FakeS3(raw=b"\x00\x01\x02\xff")

        @asynccontextmanager
        async def fake_managed_session():
            yield session

        with patch.object(file_main.settings, "s3_bucket_name", "bucket"), \
             patch.object(file_main, "_get_s3_client", lambda: fake_s3), \
             patch.object(file_main, "get_managed_session", lambda: fake_managed_session()):
            asyncio.run(file_main.handle_process_csv({
                "record_id": 8,
                "object_key": "raw/8_broken.csv",
                "filename": "broken.csv",
            }))

        self.assertEqual(record.status, "pending")
        self.assertEqual(record.retry_count, 1)
        retry_jobs = [item for item in session.added if item.__class__.__name__ == "SystemOutbox"]
        self.assertEqual(len(retry_jobs), 1)
        self.assertEqual(retry_jobs[0].payload["record_id"], 8)

        session.added.clear()
        record.retry_count = 2
        with patch.object(file_main.settings, "s3_bucket_name", "bucket"), \
             patch.object(file_main, "_get_s3_client", lambda: fake_s3), \
             patch.object(file_main, "get_managed_session", lambda: fake_managed_session()):
            asyncio.run(file_main.handle_process_csv({
                "record_id": 8,
                "object_key": "raw/8_broken.csv",
                "filename": "broken.csv",
            }))

        self.assertEqual(record.status, "failed")
        self.assertIn("Manual review required", record.error_message)
        self.assertEqual([item for item in session.added if item.__class__.__name__ == "SystemOutbox"], [])


class FileCleanerFrontendContractTests(unittest.TestCase):
    def test_frontend_contract_documents_every_promised_backend_feature(self):
        contract = (ROOT / "docs" / "features" / "filecleaner-frontend-contract.md").read_text(encoding="utf-8")
        for term in [
            "/files/analyze",
            "/files/upload",
            "/files/{id}/status",
            "/files/{id}/report",
            "/files/{id}/cancel",
            "fuzzy_matching",
            "schema_validation",
            "anomaly_detection",
            "normalization",
            "metadata stripping",
        ]:
            self.assertIn(term, contract)

    def test_dashboard_exposes_pipeline_controls_preview_and_cancel_actions(self):
        page = (ROOT / "apps" / "filecleaner" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        for term in [
            "/files/analyze",
            "/files/deep-clean",
            "/files/{fileId}/cancel",
            "Deep clean",
            "Pro",
            "Preview first 100 rows",
            "Fuzzy matching",
            "Schema validation",
            "Anomaly detection",
            "Normalization",
            "100MB",
            "Clean image or PDF",
        ]:
            self.assertIn(term, page)

    def test_cli_exposes_api_commands_for_pipeline_workflow(self):
        cli = (ROOT / "apps" / "filecleaner" / "cli" / "filecleaner.py").read_text(encoding="utf-8")
        for term in [
            "analyze",
            "upload",
            "status",
            "report",
            "cancel",
            "download",
            "/files/analyze",
            "/files/upload",
            "/files/{id}/cancel",
        ]:
            self.assertIn(term, cli)


if __name__ == "__main__":
    unittest.main()
