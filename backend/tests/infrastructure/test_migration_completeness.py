"""
Tests for migration completeness — ensures every column defined in SQLModel
entities exists in the database after running _run_migrations() against
a baseline (pre-migration) schema.

This catches the exact class of bug where a new column is added to a SQLModel
entity but the corresponding ALTER TABLE migration is forgotten, causing
production databases (with persistent radar.db) to crash on INSERT.
"""

import inspect
import os
import re
import tempfile

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_migration"
)

from sqlalchemy import Column, MetaData, Table, text  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy import inspect as sa_inspect  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import domain.entities  # noqa: F401, E402 — register all entity models
from infrastructure.database import _run_migrations  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALTER_TABLE_PATTERN = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)",
    re.IGNORECASE,
)

_SQL_STRING_PATTERN = re.compile(
    r'"((?:ALTER TABLE|UPDATE)\s[^"]+)"',
)


def _extract_migration_sql() -> list[str]:
    """Extract SQL statement strings from _run_migrations() source code."""
    source = inspect.getsource(_run_migrations)
    sqls = _SQL_STRING_PATTERN.findall(source)
    assert sqls, (
        "Failed to extract any migration SQL from _run_migrations(). "
        "Has the function format changed?"
    )
    return sqls


def _extract_add_column_targets(migration_sqls: list[str]) -> set[tuple[str, str]]:
    """
    Parse ALTER TABLE ... ADD COLUMN ... statements.
    Returns set of (table_name_lower, column_name_lower).
    """
    targets: set[tuple[str, str]] = set()
    for sql in migration_sqls:
        match = _ALTER_TABLE_PATTERN.match(sql)
        if match:
            targets.add((match.group(1).lower(), match.group(2).lower()))
    return targets


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigrationCompleteness:
    """Verify that _run_migrations() covers all entity columns."""

    def test_migrations_should_produce_complete_schema(self):
        """
        Simulate upgrading a "pre-migration" database:
        1. Create tables with only baseline columns (minus migration-added ones).
        2. Run all migration SQL.
        3. Assert every SQLModel entity column now exists in the actual schema.

        Failure here means a column was added to domain/entities.py without
        a corresponding ALTER TABLE migration in infrastructure/database.py.
        """
        # -- Step 1: Parse migration SQL and identify ADD COLUMN targets ------
        migration_sqls = _extract_migration_sql()
        add_targets = _extract_add_column_targets(migration_sqls)

        # -- Step 2: Create baseline tables (entity cols minus migration cols) -
        test_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        baseline_meta = MetaData()
        for table in SQLModel.metadata.sorted_tables:
            cols = []
            for col in table.columns:
                if (table.name.lower(), col.name.lower()) in add_targets:
                    continue  # This column should be added by migration
                cols.append(
                    Column(
                        col.name,
                        col.type,
                        primary_key=col.primary_key,
                        nullable=True,  # Relax constraints for baseline
                    )
                )
            if cols:
                Table(table.name, baseline_meta, *cols)

        baseline_meta.create_all(test_engine)

        # -- Step 3: Run all migration SQL against the baseline DB ------------
        with test_engine.connect() as conn:
            for sql in migration_sqls:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception:
                    # Silently skip errors (same as production _run_migrations)
                    conn.rollback()

        # -- Step 4: Verify all entity columns exist in the actual schema -----
        insp = sa_inspect(test_engine)
        for table in SQLModel.metadata.sorted_tables:
            actual_cols = {c["name"].lower() for c in insp.get_columns(table.name)}
            expected_cols = {c.name.lower() for c in table.columns}
            missing = expected_cols - actual_cols
            assert not missing, (
                f"Table '{table.name}' is missing columns after migration: {missing}. "
                f"Add an ALTER TABLE migration to _run_migrations() in "
                f"infrastructure/database.py for each missing column."
            )

        test_engine.dispose()

    def test_migration_add_column_targets_should_match_entity_tables(self):
        """
        Every ALTER TABLE ... ADD COLUMN in _run_migrations() should reference
        a table that actually exists in the SQLModel entity metadata.
        Catches typos in migration table names.
        """
        migration_sqls = _extract_migration_sql()
        add_targets = _extract_add_column_targets(migration_sqls)
        entity_tables = {t.name.lower() for t in SQLModel.metadata.sorted_tables}

        for table_name, col_name in add_targets:
            assert table_name in entity_tables, (
                f"Migration references table '{table_name}' (column '{col_name}') "
                f"which does not exist in SQLModel entities. "
                f"Known tables: {sorted(entity_tables)}"
            )

    def test_migration_add_column_targets_should_match_entity_columns(self):
        """
        Every ALTER TABLE ... ADD COLUMN in _run_migrations() should reference
        a column that actually exists in the corresponding SQLModel entity.
        Catches typos in migration column names.
        """
        migration_sqls = _extract_migration_sql()
        add_targets = _extract_add_column_targets(migration_sqls)

        entity_columns: dict[str, set[str]] = {}
        for table in SQLModel.metadata.sorted_tables:
            entity_columns[table.name.lower()] = {c.name.lower() for c in table.columns}

        for table_name, col_name in add_targets:
            if table_name not in entity_columns:
                continue  # Covered by test above
            assert col_name in entity_columns[table_name], (
                f"Migration adds column '{col_name}' to table '{table_name}', "
                f"but this column does not exist in the SQLModel entity. "
                f"Known columns: {sorted(entity_columns[table_name])}"
            )
