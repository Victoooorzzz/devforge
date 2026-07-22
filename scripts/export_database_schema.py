from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel


def clean_sql(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.rstrip().splitlines())


def render_schema() -> str:
    # Importing the universal application registers every product model in the
    # shared SQLModel metadata. SQLAlchemy does not connect until a query runs.
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://schema_export:schema_export@localhost/schema_export",
    )
    import backend_core.universal_main  # noqa: F401
    from backend_core.db_migrations import MIGRATION_STATEMENTS

    dialect = postgresql.dialect()
    sections = [
        "-- DevForge PostgreSQL schema",
        "-- Generated offline from SQLModel metadata and lightweight migrations.",
        "-- Contains structure only; no production credentials or customer data.",
        "",
        "BEGIN;",
        "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
        "",
    ]

    for table in SQLModel.metadata.sorted_tables:
        sections.append(clean_sql(str(CreateTable(table, if_not_exists=True).compile(dialect=dialect))) + ";")
        sections.append("")

    seen_indexes: set[str] = set()
    for table in SQLModel.metadata.sorted_tables:
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            if not index.name or index.name in seen_indexes:
                continue
            seen_indexes.add(index.name)
            sections.append(clean_sql(str(CreateIndex(index, if_not_exists=True).compile(dialect=dialect))) + ";")

    sections.extend(["", "-- Idempotent structural compatibility migrations", ""])
    structural_prefixes = ("ALTER ", "CREATE ", "DO ")
    sections.extend(
        statement.rstrip().rstrip(";") + ";"
        for statement in MIGRATION_STATEMENTS
        if statement.lstrip().upper().startswith(structural_prefixes)
    )
    sections.extend(["", "COMMIT;", ""])
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the complete DevForge PostgreSQL schema offline.")
    parser.add_argument("output", type=Path, help="Destination .sql file")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    schema = render_schema()
    args.output.write_text(schema, encoding="utf-8", newline="\n")
    print(f"Exported schema to {args.output.resolve()}")
    print(f"Tables: {len(SQLModel.metadata.tables)}")
    print(f"Bytes: {args.output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
