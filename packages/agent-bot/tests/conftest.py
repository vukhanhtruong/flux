import pytest

from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


@pytest.fixture
def sqlite_db(tmp_path):
    """Provide a migrated SQLite Database for testing."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    db.connect()
    migrate(db)
    yield db
    db.disconnect()
