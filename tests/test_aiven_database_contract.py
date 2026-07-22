from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATABASE_MODULE = REPO_ROOT / "packages" / "backend_core" / "database.py"


def test_database_pool_fits_aiven_free_connection_limit() -> None:
    source = DATABASE_MODULE.read_text(encoding="utf-8")

    assert "pool_size=3" in source
    assert "max_overflow=2" in source
    assert "pool_recycle=300" in source
