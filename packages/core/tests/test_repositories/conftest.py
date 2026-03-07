import pytest
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.connect()
    migrate(database)
    yield database
    database.disconnect()


@pytest.fixture
def conn(db):
    return db.connection()


@pytest.fixture
def user_id(conn):
    conn.execute(
        "INSERT INTO users (id, platform, platform_id, display_name) VALUES (?, ?, ?, ?)",
        ("test:user1", "test", "user1", "Test User"),
    )
    return "test:user1"
