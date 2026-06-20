import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.webhookmonitor.cli import webhookmonitor


class WebhookMonitorCliContractTests(unittest.TestCase):
    def _run(self, argv):
        calls = []

        def fake_request(method, path, payload):
            calls.append((method, path, payload))
            return {"ok": True}

        result = webhookmonitor.run(argv, request_func=fake_request)
        self.assertEqual(result, {"ok": True})
        return calls[0]

    def test_endpoints_create_uses_rest_contract(self):
        method, path, payload = self._run([
            "endpoints",
            "create",
            "--name",
            "Stripe Production",
            "--method",
            "POST",
            "--method",
            "PUT",
        ])

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/webhooks/endpoints")
        self.assertEqual(payload, {"name": "Stripe Production", "methods": ["POST", "PUT"]})

    def test_events_replay_uses_alternate_url_contract(self):
        method, path, payload = self._run([
            "events",
            "replay",
            "--id",
            "123",
            "--url",
            "https://example.com/webhook",
        ])

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/webhooks/events/123/replay")
        self.assertEqual(payload["mode"], "alternate")
        self.assertEqual(payload["target_url"], "https://example.com/webhook")

    def test_events_diff_and_search_use_backend_routes(self):
        method, path, payload = self._run(["events", "diff", "--id", "123", "--with", "122"])
        self.assertEqual((method, path, payload), ("GET", "/webhooks/events/123/diff?base_request_id=122", None))

        method, path, payload = self._run([
            "events",
            "search",
            "--json-path",
            "type",
            "--equals",
            "payment_intent.succeeded",
            "--status",
            "successful",
            "--provider",
            "stripe",
        ])
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/webhooks/search")
        self.assertEqual(payload["json_path"], "type")
        self.assertEqual(payload["equals"], "payment_intent.succeeded")
        self.assertEqual(payload["status"], "successful")
        self.assertEqual(payload["provider"], "stripe")


if __name__ == "__main__":
    unittest.main()
