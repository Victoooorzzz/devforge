import sys
import asyncio
import hashlib
import hmac
import time
import unittest
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

import apps.feedbacklens.backend.main as feedback_main
from backend_core.auth import User, get_current_user
from backend_core.database import get_session

TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


class _FakeExecuteResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalar_one(self):
        return self.rows[0] if self.rows else 0


class _FakeSession:
    def __init__(self, rows=None, item=None, responses=None):
        self.rows = list(rows or [])
        self.responses = [list(response) for response in (responses or [])]
        self.item = item
        self.added = []
        self.committed = False
        self.queries = []

    async def execute(self, _query):
        self.queries.append(_query)
        if self.responses:
            return _FakeExecuteResult(self.responses.pop(0))
        return _FakeExecuteResult(self.rows)

    async def get(self, _model, _item_id):
        return self.item

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for index, item in enumerate(self.added, start=100):
            if "id" in getattr(type(item), "model_fields", {}) and getattr(item, "id", None) is None:
                item.id = index

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = 100

    async def commit(self):
        self.committed = True


def _trial_user():
    return User(
        id=42,
        email="owner@example.test",
        hashed_password="unused",
        trial_ends_at=datetime.utcnow() + timedelta(days=1),
    )


def _client(session):
    feedback_main.app.dependency_overrides.clear()
    feedback_main.app.dependency_overrides[get_current_user] = _trial_user

    async def override_session():
        yield session

    feedback_main.app.dependency_overrides[get_session] = override_session
    return TestClient(feedback_main.app)


class FeedbackLensProductionPipelineTests(unittest.TestCase):
    def tearDown(self):
        feedback_main.app.dependency_overrides.clear()

    def test_feedbacklens_uses_local_analysis_without_gemini_or_ai_copy(self):
        backend = (ROOT / "apps" / "feedbacklens" / "backend" / "main.py").read_text(encoding="utf-8")
        product = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "config" / "product.ts").read_text(encoding="utf-8")
        landing = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
        settings = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "dashboard" / "settings" / "page.tsx").read_text(encoding="utf-8")

        for text in (backend, product, landing, settings):
            self.assertNotIn("Gemini", text)
            self.assertNotIn("genai", text)
            self.assertNotIn("AI-Powered", text)
            self.assertNotIn("AI analysis", text)
        self.assertIn("Local sentiment analysis", product)
        self.assertIn("Local Analysis Preferences", settings)

    def test_analyze_and_draft_reply_are_local_and_deterministic(self):
        entry = feedback_main.FeedbackEntry(
            id=7,
            user_id=42,
            text="Export is broken and I need a refund urgently",
            created_at=datetime.utcnow(),
        )
        session = _FakeSession(responses=[[entry], []], item=entry)
        client = _client(session)

        analyzed = client.post("/feedback/7/analyze")
        drafted = client.post("/feedback/7/draft-reply")

        self.assertEqual(analyzed.status_code, 200)
        self.assertEqual(drafted.status_code, 200)
        self.assertIn(analyzed.json()["analysis_engine"], {"enhanced_keyword", "local_transformers", "keyword"})
        self.assertNotEqual(analyzed.json()["analysis_engine"], "gemini")
        self.assertTrue(drafted.json()["draft_reply"])
        self.assertNotIn("Gemini", drafted.json()["draft_reply"])

    def test_software_failure_words_outweigh_single_positive_phrase(self):
        analysis = feedback_main._analyze_feedback_locally(
            "The mobile app crashes every time I try to export a PDF. "
            "This is blocking our entire sales team. Also, dark mode is amazing "
            "but the contrast is too low. Please fix the export ASAP."
        )

        self.assertEqual(analysis["sentiment"], "negative")
        self.assertTrue(analysis["is_urgent"])
        self.assertIn("export", analysis["themes"])

    def test_refactor_uses_timezone_aware_enhanced_keyword_engine_without_vader(self):
        backend = (ROOT / "apps" / "feedbacklens" / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIsNotNone(feedback_main._utc_now().tzinfo)
        self.assertEqual(feedback_main._utc_now().utcoffset(), timezone.utc.utcoffset(None))
        self.assertNotIn("vaderSentiment", backend)

        analysis = feedback_main._analyze_feedback_locally("The export flow is not bad and works perfectly.")
        self.assertEqual(analysis["sentiment"], "positive")
        self.assertEqual(analysis["engine"], "enhanced_keyword")

    def test_spam_detector_returns_score_and_reasons(self):
        result = feedback_main._is_spam_feedback_v2(
            "BUY NOW click here limited offer http://spam.example http://bad.example !!!"
        )

        self.assertTrue(result["is_spam"])
        self.assertGreaterEqual(result["score"], 3)
        self.assertTrue(result["reasons"])

    def test_simhash_duplicate_detector_catches_large_batch_duplicates(self):
        candidates = [
            feedback_main.FeedbackEntry(id=1, user_id=42, text="Checkout crashes when I add my card"),
            feedback_main.FeedbackEntry(id=2, user_id=42, text="Weekly summary is useful"),
        ]

        duplicate = feedback_main._find_duplicate_simhash("The checkout crashed after adding a card", candidates)

        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.id, 1)

    def test_auth_failure_feedback_is_negative_and_urgent(self):
        analysis = feedback_main._analyze_feedback_locally(
            "I cannot login with my Google account. It says Unauthorized but I paid for Pro. Help!"
        )

        self.assertEqual(analysis["sentiment"], "negative")
        self.assertTrue(analysis["is_urgent"])
        self.assertIn("login", analysis["themes"])

    def test_simple_positive_feedback_is_positive(self):
        analysis = feedback_main._analyze_feedback_locally("I love the new dashboard design.")

        self.assertEqual(analysis["sentiment"], "positive")
        self.assertFalse(analysis["is_urgent"])

    def test_positive_feedback_with_negated_failure_stays_positive(self):
        analysis = feedback_main._analyze_feedback_locally(
            "The login is not broken, it works great and feels reliable."
        )

        self.assertEqual(analysis["sentiment"], "positive")
        self.assertFalse(analysis["is_urgent"])

    def test_positive_login_feedback_is_not_a_failure(self):
        analysis = feedback_main._analyze_feedback_locally("I love the new login design.")

        self.assertEqual(analysis["sentiment"], "positive")
        self.assertFalse(analysis["is_urgent"])

    def test_login_only_counts_as_failure_near_problem_words(self):
        score = feedback_main._software_failure_score("I love the new login design. Checkout is broken.")

        self.assertEqual(score, 1)

    def test_unicode_feedback_normalization_preserves_non_english_terms(self):
        normalized = feedback_main._normalize_feedback_text("crédito über 中文反馈")

        self.assertIn("crédito", normalized)
        self.assertIn("über", normalized)
        self.assertIn("中文反馈", normalized)

    def test_urgent_feedback_alert_escapes_user_html(self):
        entry = feedback_main.FeedbackEntry(
            user_id=42,
            text="<img src=x onerror=alert(1)>",
            is_urgent=True,
            source="<script>alert('source')</script>",
            author="<b>attacker</b>",
            cluster_slug="<svg/onload=alert(2)>",
        )
        session = _FakeSession(responses=[[SimpleNamespace(alert_email="owner@example.test")]])

        asyncio.run(feedback_main._queue_urgent_feedback_alert(entry, session))

        html_body = session.added[0].payload["html_body"]
        self.assertIn("&lt;img", html_body)
        self.assertIn("&lt;script&gt;", html_body)
        self.assertIn("&lt;b&gt;attacker&lt;/b&gt;", html_body)
        self.assertIn("&lt;svg/onload=alert(2)&gt;", html_body)
        self.assertNotIn("<img src=x", html_body)
        self.assertNotIn("<script>", html_body)
        self.assertNotIn("<b>attacker</b>", html_body)
        self.assertNotIn("<svg/onload", html_body)

    def test_local_transformer_timeout_falls_back_to_enhanced_keywords(self):
        def slow_transformer(_text, _focus_terms=""):
            time.sleep(0.2)
            return {"sentiment": "positive", "confidence": 0.99, "themes": [], "is_urgent": False, "draft_reply": "", "engine": "local_transformers"}

        with patch.dict(feedback_main.os.environ, {"FEEDBACKLENS_ANALYSIS_ENGINE": "local_transformers"}, clear=False), \
             patch.object(feedback_main, "FEEDBACKLENS_LOCAL_ANALYSIS_TIMEOUT_SECONDS", 0.01), \
             patch.object(feedback_main, "_analyze_with_local_transformers_sync", slow_transformer):
            analysis = asyncio.run(feedback_main._analyze_feedback_locally_async("Checkout is broken and urgent"))

        self.assertEqual(analysis["engine"], "enhanced_keyword")
        self.assertEqual(analysis["sentiment"], "negative")

    def test_unconfigured_oauth_connectors_return_service_unavailable(self):
        backend = (ROOT / "apps" / "feedbacklens" / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn('status_code=503, detail="Twitter/X OAuth client is not configured."', backend)
        self.assertIn('status_code=503, detail="Reddit OAuth client is not configured."', backend)
        self.assertIn('status_code=503, detail="GitHub OAuth client is not configured."', backend)
        self.assertNotIn('status_code=500, detail="Twitter/X OAuth client is not configured."', backend)
        self.assertNotIn('status_code=500, detail="Reddit OAuth client is not configured."', backend)
        self.assertNotIn('status_code=500, detail="GitHub OAuth client is not configured."', backend)

    def test_dedupe_summary_endpoint_groups_near_duplicates(self):
        rows = [
            SimpleNamespace(id=1, text="Checkout crashes when I add my card", created_at=datetime.utcnow()),
            SimpleNamespace(id=2, text="The checkout crashed after adding a card", created_at=datetime.utcnow()),
            SimpleNamespace(id=3, text="Weekly summary is useful", created_at=datetime.utcnow()),
        ]
        response = _client(_FakeSession(rows=rows)).get("/feedback/dedupe/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_feedback"], 3)
        self.assertEqual(payload["duplicate_groups"], 1)
        self.assertEqual(payload["duplicate_candidates"], 2)
        self.assertGreater(payload["dedupe_rate"], 0)
        self.assertEqual(payload["groups"][0]["canonical_id"], 1)

    def test_frontend_contract_docs_exist_for_feedbacklens(self):
        contract = ROOT / "docs" / "features" / "feedbacklens-frontend-contract.md"
        pipeline = ROOT / "docs" / "features" / "feedbacklens-production-pipeline.md"

        self.assertTrue(contract.exists())
        self.assertTrue(pipeline.exists())
        self.assertIn("/feedback/dedupe/summary", contract.read_text(encoding="utf-8"))
        self.assertIn("Local sentiment analysis", pipeline.read_text(encoding="utf-8"))

    def test_dashboard_analysis_and_reply_actions_have_timeout_guardrails(self):
        page = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("FEEDBACK_ACTION_TIMEOUT_MS", page)
        self.assertIn("AbortController", page)
        self.assertIn("runFeedbackActionWithTimeout", page)
        self.assertIn("signal: controller.signal", page)
        self.assertIn("took too long", page)

    def test_feedback_delete_source_management_and_derived_refresh_contracts(self):
        page = (ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("handleDeleteFeedback", page)
        self.assertIn("handleCreateSource", page)
        self.assertIn("handleDeleteSource", page)
        self.assertIn("refreshDerivedInsights", page)
        self.assertIn("/feedback/${entry.id}", page)
        self.assertIn("/sources/${source.id}", page)

    def test_delete_feedback_removes_only_owned_entry(self):
        entry = feedback_main.FeedbackEntry(id=22, user_id=42, text="Remove me")
        session = _FakeSession(rows=[entry])

        response = _client(session).delete("/feedback/22")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "deleted")
        self.assertTrue(any(str(query).lstrip().upper().startswith("DELETE") for query in session.queries))

    def test_source_list_excludes_deleted_sources_and_reanalysis_updates_derived_fields(self):
        list_session = _FakeSession(rows=[])
        response = _client(list_session).get("/sources")
        self.assertEqual(response.status_code, 200)
        self.assertIn("feedback_sources.status", str(list_session.queries[0]))

        backend = (ROOT / "apps" / "feedbacklens" / "backend" / "main.py").read_text(encoding="utf-8")
        analyze_block = backend[backend.index("async def analyze_feedback"):backend.index("async def process_feedback_analysis")]
        self.assertIn("_apply_local_processing_async", analyze_block)

    def test_pricing_copy_matches_feedbacklens_limits(self):
        files = [
            ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "config" / "product.ts",
            ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "page.tsx",
            ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "register" / "page.tsx",
            ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "terms" / "page.tsx",
            ROOT / "apps" / "feedbacklens" / "frontend" / "src" / "app" / "refunds" / "page.tsx",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

        self.assertIn("$19", combined)
        self.assertIn("5000", combined)
        self.assertNotIn("$9.99", combined)
        self.assertNotIn("Unlimited", combined)

    def test_feedback_entry_has_source_message_unique_constraint(self):
        constraints = {
            tuple(column.name for column in constraint.columns)
            for constraint in feedback_main.FeedbackEntry.__table__.constraints
            if getattr(constraint, "unique", False) or constraint.__class__.__name__ == "UniqueConstraint"
        }
        constraints.update(
            tuple(column.name for column in index.columns)
            for index in feedback_main.FeedbackEntry.__table__.indexes
            if index.unique
        )

        self.assertIn(("user_id", "source", "source_message_id"), constraints)

    def test_create_source_encrypts_new_tokens_and_webhook_secret(self):
        session = _FakeSession(responses=[[], []])
        client = _client(session)

        async def allow_source(_user, _source_type, _session):
            return None

        with patch.dict(feedback_main.os.environ, {"ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}, clear=False), \
             patch.object(feedback_main, "_enforce_source_limit", allow_source):
            response = client.post(
                "/sources",
                json={
                    "source_type": "github",
                    "display_name": "GitHub",
                    "access_token": "gh-token",
                    "refresh_token": "refresh-token",
                    "webhook_secret": "webhook-secret",
                    "repo": "owner/repo",
                },
            )

        self.assertEqual(response.status_code, 200)
        source = session.added[0]
        self.assertNotEqual(source.access_token, "gh-token")
        self.assertNotEqual(source.refresh_token, "refresh-token")
        self.assertNotEqual(source.webhook_secret, "webhook-secret")
        self.assertTrue(source.access_token.startswith("enc:"))
        with patch.dict(feedback_main.os.environ, {"ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}, clear=False):
            self.assertEqual(feedback_main.decrypt_secret(source.access_token), "gh-token")
            self.assertEqual(feedback_main.decrypt_secret(source.refresh_token), "refresh-token")
            self.assertEqual(feedback_main.decrypt_secret(source.webhook_secret), "webhook-secret")

    def test_encrypting_new_source_secret_requires_encryption_key(self):
        session = _FakeSession(responses=[[], []])
        client = _client(session)

        async def allow_source(_user, _source_type, _session):
            return None

        client = TestClient(feedback_main.app, raise_server_exceptions=False)
        with patch.dict(feedback_main.os.environ, {"ENCRYPTION_KEY": ""}, clear=False), \
             patch.object(feedback_main, "_enforce_source_limit", allow_source):
            response = client.post(
                "/sources",
                json={"source_type": "github", "access_token": "gh-token"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(session.added, [])

    def test_handle_feedback_email_runs_send_email_off_event_loop(self):
        async def exercise():
            calls = []

            def fake_send_email(**kwargs):
                calls.append(kwargs)

            async def fake_run_in_thread(func, *args, **kwargs):
                calls.append({"runner": True})
                func(*args, **kwargs)

            with patch.object(feedback_main, "send_email", fake_send_email), \
                 patch.object(feedback_main, "_run_in_thread", fake_run_in_thread):
                result = await feedback_main.handle_feedback_email({
                    "to": "owner@example.test",
                    "subject": "Digest",
                    "html_body": "<p>Hello</p>",
                })
            return calls, result

        calls, result = asyncio.run(exercise())

        self.assertEqual(calls[0], {"runner": True})
        self.assertEqual(calls[1]["to"], "owner@example.test")
        self.assertEqual(result["status"], "sent")

    def test_github_webhook_rejects_missing_secret_before_accepting_signature(self):
        body = b'{"action":"opened","issue":{"id":1,"title":"Checkout broken","body":"Please fix"}}'
        source = feedback_main.FeedbackSource(id=9, user_id=42, source_type="github", webhook_secret="")
        session = _FakeSession(responses=[[source]])
        raw_signature = hmac.new(b"", body, hashlib.sha256).hexdigest()
        client = TestClient(feedback_main.app)

        async def override_session():
            yield session

        feedback_main.app.dependency_overrides[get_session] = override_session

        response = client.post(
            "/feedback/ingest/github?source_id=9",
            content=body,
            headers={"x-hub-signature-256": f"sha256={raw_signature}"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("secret", response.json()["detail"].lower())

    def test_bulk_csv_rejects_non_csv_content_type(self):
        session = _FakeSession(rows=[])
        _client(session)

        response = TestClient(feedback_main.app).post(
            "/feedback/bulk-csv",
            files={"file": ("feedback.json", b'{"text":"hello"}', "application/json")},
        )

        self.assertEqual(response.status_code, 415)

    def test_clean_feedback_text_truncates_long_text_without_spaces(self):
        text = "界" * (feedback_main.FEEDBACK_TEXT_LIMIT + 50)

        cleaned = feedback_main._clean_feedback_text(text)

        self.assertEqual(len(cleaned), feedback_main.FEEDBACK_TEXT_LIMIT)
        self.assertTrue(cleaned)

    def test_entry_from_payload_rejects_invalid_or_missing_text(self):
        with self.assertRaises(ValueError):
            feedback_main._entry_from_payload({"id": object(), "text": ""}, user_id=42)

    def test_feedback_prefs_rejects_invalid_alert_email(self):
        session = _FakeSession(responses=[[]])
        client = _client(session)

        response = client.put(
            "/settings/feedback-prefs",
            json={"alert_email": "not-an-email", "negative_threshold": 0.5},
        )

        self.assertEqual(response.status_code, 422)

    def test_compound_cluster_terms_win_over_generic_terms(self):
        self.assertEqual(
            feedback_main._cluster_slug_for_analysis("Please add dark mode to the dashboard"),
            "dark-mode",
        )
        self.assertEqual(
            feedback_main._cluster_slug_for_analysis("CSV export is broken"),
            "export",
        )

    def test_dedupe_candidate_query_is_bounded_well_below_legacy_500(self):
        session = _FakeSession(rows=[])

        asyncio.run(feedback_main._load_dedupe_candidates(42, session, text="checkout card crashes"))

        limit_clause = session.queries[0]._limit_clause
        self.assertIsNotNone(limit_clause)
        self.assertLessEqual(int(limit_clause.value), 50)

    def test_bulk_import_loads_existing_candidates_once(self):
        session = _FakeSession(rows=[])
        calls = []

        async def fake_load(*_args, **_kwargs):
            calls.append(True)
            return []

        async def fake_process(entry, **_kwargs):
            entry.sentiment = "neutral"
            entry.themes_json = "[]"
            entry.analysis_engine = "enhanced_keyword"
            entry.cluster_slug = "general"
            entry.priority = "low"
            return {}

        async def no_alert(*_args, **_kwargs):
            return None

        async def allow_limit(*_args, **_kwargs):
            return None

        body = feedback_main.BulkImportRequest(texts=[
            "Checkout button is misaligned",
            "Weekly digest needs a date filter",
            "Mobile navigation needs larger labels",
        ])
        with patch.object(feedback_main, "_load_dedupe_candidates", fake_load), \
             patch.object(feedback_main, "_apply_local_processing_async", fake_process), \
             patch.object(feedback_main, "_queue_urgent_feedback_alert", no_alert), \
             patch.object(feedback_main, "_enforce_feedback_limit", allow_limit):
            result = asyncio.run(feedback_main.bulk_import_feedback(body, _trial_user(), session))

        self.assertEqual(result["created"], 3)
        self.assertEqual(len(calls), 1)

    def test_csv_export_defers_database_reads_to_streaming_batches(self):
        session = _FakeSession(rows=[])

        response = asyncio.run(feedback_main.export_feedback("csv", _trial_user(), session))

        self.assertEqual(session.queries, [])
        self.assertEqual(response.media_type, "text/csv")
        self.assertTrue(hasattr(response.body_iterator, "__aiter__"))

    def test_heavy_local_ml_is_explicitly_opt_in(self):
        feedback_main._sentiment_pipeline = None
        real_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith(("transformers", "optimum")):
                raise RuntimeError("heavy ML import attempted")
            return real_import(name, *args, **kwargs)

        with patch.dict(feedback_main.os.environ, {"FEEDBACKLENS_ENABLE_LOCAL_ML": "0"}, clear=False), \
             patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(RuntimeError, "disabled"):
                feedback_main._get_sentiment_pipeline()

    def test_priority_helper_has_no_dead_mention_count_parameter(self):
        parameters = inspect.signature(feedback_main._priority_for_analysis).parameters

        self.assertNotIn("mention_count", parameters)

    def test_cleaning_raises_business_exception_instead_of_http_exception(self):
        with self.assertRaises(feedback_main.SpamDetectedError):
            feedback_main._clean_feedback_text(
                "BUY NOW click here limited offer http://spam.example http://bad.example !!!"
            )

    def test_source_config_is_schema_validated(self):
        invalid = feedback_main.FeedbackSource(
            user_id=42,
            source_type="github",
            config_json='{"repo": 123, "oauth_state": ["bad"]}',
        )

        self.assertEqual(feedback_main._source_config(invalid), {})

    def test_github_webhook_payload_is_schema_validated(self):
        payload = feedback_main.GitHubWebhookPayload.model_validate_json(
            '{"action":"opened","issue":{"id":123,"title":"Broken checkout","body":"Help",'
            '"user":{"login":"victor"}}}'
        )

        self.assertEqual(payload.issue.id, 123)
        with self.assertRaises(Exception):
            feedback_main.GitHubWebhookPayload.model_validate_json(
                '{"action":"opened","issue":{"id":{"nested":true}}}'
            )

    def test_public_webhook_rate_limit_uses_persisted_completed_outbox_rows(self):
        session = _FakeSession(responses=[[0]])

        asyncio.run(feedback_main._enforce_public_webhook_rate_limit(9, session))

        record = session.added[0]
        self.assertEqual(record.status, "completed")
        self.assertEqual(record.app_name, "feedbacklens-rate-9")
        self.assertEqual(record.job_type, "github_ingest")

    def test_outbound_http_validation_rejects_ssrf_targets(self):
        with self.assertRaises(ValueError):
            feedback_main._validate_outbound_url("http://127.0.0.1:8000/private")
        with self.assertRaises(ValueError):
            feedback_main._validate_outbound_url("https://localhost/admin")

        self.assertEqual(
            feedback_main._validate_outbound_url("https://api.github.com/repos/acme/app/issues"),
            "https://api.github.com/repos/acme/app/issues",
        )

    def test_feedback_cursor_round_trips_created_at_and_id(self):
        created_at = datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc)

        encoded = feedback_main._encode_feedback_cursor(created_at, 321)
        decoded_at, decoded_id = feedback_main._decode_feedback_cursor(encoded)

        self.assertEqual(decoded_at, created_at)
        self.assertEqual(decoded_id, 321)

    def test_dedupe_summary_prefilters_pairs_before_semantic_similarity(self):
        entries = [
            SimpleNamespace(
                id=index,
                text=f"topic-{index:02d}-{'alpha' if index % 3 == 0 else 'zulu' if index % 3 == 1 else 'quartz'}",
                created_at=datetime.now(timezone.utc),
            )
            for index in range(1, 31)
        ]
        calls = []

        def tracked(left, right):
            calls.append((left, right))
            return 0.0

        with patch.object(feedback_main, "_semantic_similarity", tracked):
            feedback_main._build_dedupe_summary(entries)

        all_pairs = len(entries) * (len(entries) - 1) // 2
        self.assertLess(len(calls), all_pairs // 3)

    def test_contextual_spam_terms_do_not_reject_legitimate_domain_feedback(self):
        result = feedback_main._is_spam_feedback_v2(
            "Our investment opportunity page is documented at https://example.com/docs"
        )

        self.assertFalse(result["is_spam"])

    def test_spam_terms_and_whitelist_are_configurable(self):
        result = feedback_main._is_spam_feedback_v2(
            "casino promo click here https://spam.example",
            custom_terms=("casino promo",),
            whitelist=("casino promo",),
        )

        self.assertFalse(result["is_spam"])

    def test_feedback_entries_track_real_updated_and_analyzed_times(self):
        self.assertIn("updated_at", feedback_main.FeedbackEntry.model_fields)
        self.assertIn("analyzed_at", feedback_main.FeedbackEntry.model_fields)
        entry = feedback_main.FeedbackEntry(user_id=1, text="Checkout is broken")
        now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)

        with patch.object(feedback_main, "_utc_now", return_value=now):
            feedback_main._apply_local_processing(entry)

        self.assertEqual(entry.updated_at, now)
        self.assertEqual(entry.analyzed_at, now)

    def test_cluster_build_is_linear_and_uses_persisted_cluster_slug(self):
        entries = [
            SimpleNamespace(
                id=index,
                cluster_slug="checkout",
                priority="high",
                text=f"Checkout issue {index}",
                sentiment="negative",
                created_at=datetime.now(timezone.utc),
            )
            for index in range(100)
        ]
        with patch.object(feedback_main, "_semantic_similarity", side_effect=AssertionError("pairwise rebuild")):
            clusters = feedback_main._build_cluster_payloads(entries)

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["mention_count"], 100)

    def test_topic_and_urgent_terms_are_configurable(self):
        with patch.dict(
            feedback_main.os.environ,
            {
                "FEEDBACKLENS_TOPIC_TERMS": "observability",
                "FEEDBACKLENS_URGENT_TERMS": "security",
            },
            clear=False,
        ):
            self.assertEqual(
                feedback_main._cluster_slug_for_analysis("Alpha observability feedback"),
                "observability",
            )
            self.assertEqual(
                feedback_main._priority_for_analysis(
                    {"themes": ["security"], "sentiment": "neutral", "is_urgent": False}
                ),
                "urgent",
            )

    def test_support_draft_is_topic_specific(self):
        draft = feedback_main._support_draft("negative", False, ["billing"])

        self.assertIn("billing", draft.lower())

    def test_oauth_refresh_rotates_encrypted_source_token(self):
        source = feedback_main.FeedbackSource(
            user_id=1,
            source_type="reddit",
            display_name="Reddit",
            refresh_token="enc:old-refresh",
        )
        with patch.object(feedback_main, "decrypt_secret", return_value="refresh-token"), \
             patch.object(feedback_main, "encrypt_secret", side_effect=lambda value: f"enc:{value}"), \
             patch.object(feedback_main, "_reddit_client_id", return_value="client-id"), \
             patch.object(feedback_main, "_reddit_client_secret", return_value="client-secret"), \
             patch.object(
                 feedback_main,
                 "_http_form_json",
                 return_value={"access_token": "new-access", "refresh_token": "new-refresh"},
             ):
            refreshed = feedback_main._refresh_oauth_source(source)

        self.assertTrue(refreshed)
        self.assertEqual(source.access_token, "enc:new-access")
        self.assertEqual(source.refresh_token, "enc:new-refresh")

    def test_feedback_stemmer_normalizes_common_inflections(self):
        self.assertEqual(
            feedback_main._stem_feedback_token("running"),
            feedback_main._stem_feedback_token("runs"),
        )


if __name__ == "__main__":
    unittest.main()
