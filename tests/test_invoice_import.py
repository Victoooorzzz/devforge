import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from apps.invoicefollow.backend.main import InvoiceCreate, _parse_invoice_import


class InvoiceImportTests(unittest.TestCase):
    def test_invoice_create_rejects_non_positive_amount(self):
        with self.assertRaises(ValidationError):
            InvoiceCreate(
                client_name="Acme",
                client_email="billing@example.com",
                amount=0,
                due_date="2026-07-01",
            )

    def test_parses_valid_csv_rows_into_invoice_payloads(self):
        content = (
            "client_name,client_email,amount,due_date\n"
            "Acme,billing@example.com,120.50,2026-07-01\n"
            "Globex,ap@globex.com,90,2026-07-15\n"
        ).encode("utf-8")

        invoices = _parse_invoice_import(content, "invoices.csv")

        self.assertEqual(len(invoices), 2)
        self.assertEqual(invoices[0].client_name, "Acme")
        self.assertEqual(invoices[0].amount, 120.50)

    def test_import_reports_row_errors_without_silent_partial_success(self):
        content = (
            "client_name,client_email,amount,due_date\n"
            "Acme,billing@example.com,120.50,2026-07-01\n"
            "Broken,not-an-email,-5,not-a-date\n"
        ).encode("utf-8")

        with self.assertRaises(ValueError) as raised:
            _parse_invoice_import(content, "invoices.csv")

        message = str(raised.exception)
        self.assertIn("Row 3", message)
        self.assertIn("client_email", message)
        self.assertIn("amount", message)
        self.assertIn("due_date", message)


if __name__ == "__main__":
    unittest.main()
