import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import BackgroundTasks, Response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from backend_core.auth import RegisterRequest, User, register


class _EmptyResult:
    def scalar_one_or_none(self):
        return None


class _RegisterSession:
    def __init__(self):
        self.added = []
        self.commits = 0

    async def execute(self, _query):
        return _EmptyResult()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for index, item in enumerate(self.added, start=1):
            if getattr(item, "id", None) is None:
                item.id = index

    async def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = len(self.added) or 1

    async def commit(self):
        self.commits += 1


class AuthRegistrationTests(unittest.TestCase):
    def test_register_stores_trimmed_name(self):
        session = _RegisterSession()

        with patch("backend_core.auth.hash_password", return_value="hashed-password"):
            result = asyncio.run(
                register(
                    RegisterRequest(
                        name="  Victor DevForge  ",
                        email="victor+auth-test@devforgeapp.pro",
                        password="strong-password",
                    ),
                    BackgroundTasks(),
                    Response(),
                    session,
                ),
            )

        self.assertIsNotNone(result.access_token)
        self.assertEqual(session.commits, 1)
        self.assertEqual(len(session.added), 1)
        self.assertIsInstance(session.added[0], User)
        self.assertEqual(session.added[0].name, "Victor DevForge")

    def test_register_stores_blank_name_as_none(self):
        session = _RegisterSession()

        with patch("backend_core.auth.hash_password", return_value="hashed-password"):
            asyncio.run(
                register(
                    RegisterRequest(
                        name="   ",
                        email="blank-name@devforgeapp.pro",
                        password="strong-password",
                    ),
                    BackgroundTasks(),
                    Response(),
                    session,
                ),
            )

        self.assertIsNone(session.added[0].name)


if __name__ == "__main__":
    unittest.main()
