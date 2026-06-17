import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from apps.filecleaner.backend.main import _load_df, _save_df


class FileCleanerFormatTests(unittest.TestCase):
    def test_loads_json_records_as_dataframe(self):
        content = b'[{"email":" A@example.COM ","amount":"$10.00"},{"email":"b@example.com","amount":"$20.00"}]'

        df = _load_df(content, "customers.json")

        self.assertEqual(list(df.columns), ["email", "amount"])
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["email"], " A@example.COM ")

    def test_saves_dataframe_as_json_records_for_json_files(self):
        df = pd.DataFrame([
            {"email": "a@example.com", "amount": 10.0},
            {"email": "b@example.com", "amount": 20.0},
        ])

        payload = json.loads(_save_df(df, "customers.json").getvalue().decode("utf-8"))

        self.assertEqual(payload, [
            {"email": "a@example.com", "amount": 10.0},
            {"email": "b@example.com", "amount": 20.0},
        ])


if __name__ == "__main__":
    unittest.main()
