import pytest

from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.sqlite.migrations.migrate import migrate as run_core_migrations


@pytest.fixture
def sqlite_db(tmp_path):
    """Provide a migrated SQLite Database for testing."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    db.connect()
    migrate(db)
    yield db
    db.disconnect()


@pytest.fixture
def core_db(tmp_path):
    """Real temp SQLite database with core migrations applied (shared across test suites)."""
    path = tmp_path / "flux.db"
    db = Database(str(path))
    db.connect()
    run_core_migrations(db)
    try:
        yield db
    finally:
        db.disconnect()
