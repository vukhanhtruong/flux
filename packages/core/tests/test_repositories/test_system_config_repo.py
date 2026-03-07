"""Tests for SystemConfig repository."""
from pathlib import Path

from flux_core.services.encryption import EncryptionService
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository


def _make_db(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    migrate(db)
    return db


def _make_repo(db: Database, secret: str = "test-secret"):
    enc = EncryptionService(secret)
    return SqliteSystemConfigRepository(db.connection(), enc)


def test_set_and_get_plaintext(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    repo.set("s3_endpoint", "https://r2.example.com")
    assert repo.get("s3_endpoint") == "https://r2.example.com"
    db.disconnect()


def test_set_and_get_encrypted(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    repo.set("s3_secret_key", "super-secret-123", encrypted=True)
    result = repo.get("s3_secret_key")
    assert result == "super-secret-123"
    row = db.fetchone(
        "SELECT value, encrypted FROM system_config WHERE key = ?", ("s3_secret_key",)
    )
    assert row["encrypted"] == 1
    assert row["value"] != "super-secret-123"
    db.disconnect()


def test_get_nonexistent_returns_none(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    assert repo.get("nonexistent") is None
    db.disconnect()


def test_set_overwrites(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    repo.set("key", "value1")
    repo.set("key", "value2")
    assert repo.get("key") == "value2"
    db.disconnect()


def test_get_all(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    repo.set("a", "1")
    repo.set("b", "2", encrypted=True)
    all_config = repo.get_all()
    assert all_config == {"a": "1", "b": "2"}
    db.disconnect()


def test_delete(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    repo.set("key", "value")
    repo.delete("key")
    assert repo.get("key") is None
    db.disconnect()


def test_get_by_prefix(tmp_path):
    db = _make_db(tmp_path)
    repo = _make_repo(db)
    repo.set("s3_endpoint", "https://r2.example.com")
    repo.set("s3_bucket", "my-bucket")
    repo.set("backup_retention", "7")
    result = repo.get_by_prefix("s3_")
    assert result == {"s3_endpoint": "https://r2.example.com", "s3_bucket": "my-bucket"}
    db.disconnect()
