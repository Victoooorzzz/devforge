import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UiApiParityContractTests(unittest.TestCase):
    def assert_contracts(self, backend_path: str, frontend_paths: list[str], contracts: list[tuple[str, str]]) -> None:
        backend = (ROOT / backend_path).read_text(encoding="utf-8")
        frontend = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in frontend_paths)
        for backend_token, frontend_token in contracts:
            self.assertIn(backend_token, backend)
            self.assertIn(frontend_token, frontend)

    def test_webhookmonitor_ui_covers_core_mutating_and_investigation_api(self):
        self.assert_contracts(
            "apps/webhookmonitor/backend/main.py",
            [
                "apps/webhookmonitor/frontend/src/app/dashboard/page.tsx",
                "apps/webhookmonitor/frontend/src/app/dashboard/settings/page.tsx",
            ],
            [
                ('@webhook_router.delete("/endpoints/{endpoint_id}")', "/webhooks/endpoints/${endpoint.id}"),
                ('@webhook_router.delete("/requests")', "/webhooks/requests?confirm=CONFIRM"),
                ('@webhook_router.post("/search")', '"/webhooks/search"'),
                ('@webhook_router.post("/events/{request_id}/replay")', "/events/${selected.id}/replay"),
            ],
        )

    def test_filecleaner_ui_covers_processing_review_and_lifecycle_api(self):
        self.assert_contracts(
            "apps/filecleaner/backend/main.py",
            ["apps/filecleaner/frontend/src/app/dashboard/page.tsx"],
            [
                ('@file_router.post("/deep-clean")', '"/files/deep-clean"'),
                ('@file_router.post("/ai-analyze")', '"/files/ai-analyze"'),
                ('@file_router.post("/{file_id}/cancel")', "CANCEL_ENDPOINT_TEMPLATE"),
                ('@file_router.delete("/{file_id}")', "/files/${fileId}"),
            ],
        )

    def test_pricetrackr_ui_covers_tracker_configuration_and_export_api(self):
        self.assert_contracts(
            "apps/pricetrackr/backend/main.py",
            [
                "apps/pricetrackr/frontend/src/app/dashboard/components/DashboardClient.tsx",
                "apps/pricetrackr/frontend/src/app/dashboard/components/ExportButton.tsx",
            ],
            [
                ('@tracker_router.patch("/{tracker_id}/frequency")', "/trackers/${id}/frequency"),
                ('@tracker_router.patch("/{tracker_id}/alert-threshold")', "/trackers/${id}/alert-threshold"),
                ('@tracker_router.delete("/{tracker_id}")', "/trackers/${id}"),
                ('@tracker_router.get("/export-file")', "/trackers/export-file?format=${format}"),
            ],
        )

    def test_feedbacklens_ui_covers_feedback_and_source_lifecycle_api(self):
        self.assert_contracts(
            "apps/feedbacklens/backend/main.py",
            ["apps/feedbacklens/frontend/src/app/dashboard/page.tsx"],
            [
                ('@feedback_router.delete("/{entry_id}")', "/feedback/${entry.id}"),
                ('@feedback_router.post("/{entry_id}/analyze")', "/feedback/${id}/analyze"),
                ('@sources_router.post("")', '"/sources"'),
                ('@sources_router.delete("/{source_id}")', "/sources/${source.id}"),
            ],
        )

    def test_invoicefollow_ui_covers_detect_edit_delete_and_sequence_api(self):
        self.assert_contracts(
            "apps/invoicefollow/backend/main.py",
            ["apps/invoicefollow/frontend/src/app/dashboard/page.tsx"],
            [
                ('@invoice_router.post("/detect-email")', '"/invoices/detect-email"'),
                ('@invoice_router.post("/drafts/{draft_id}/confirm")', "/invoices/drafts/${detectedDraft.draft_id}/confirm"),
                ('@invoice_router.put("/{invoice_id}")', "/invoices/${editingInvoiceId}"),
                ('@invoice_router.delete("/{invoice_id}")', "/invoices/${invoice.id}"),
                ('@invoice_router.post("/{invoice_id}/pause")', "/invoices/${id}/${action}"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
