"""Fixtures for CLI tests."""
import pytest

from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate as run_core_migrations


@pytest.fixture
def cli_db(tmp_path):
    """Temp SQLite database with all migrations applied — for CLI tests."""
    db_path = str(tmp_path / "flux_cli_test.db")
    db = Database(db_path)
    db.connect()
    run_core_migrations(db)
    try:
        yield db
    finally:
        db.disconnect()
