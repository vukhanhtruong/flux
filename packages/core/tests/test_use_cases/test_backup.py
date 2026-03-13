"""Tests for backup use cases."""
import os
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from flux_core.models.backup import BackupMetadata
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.delete_backup import DeleteBackup
from flux_core.use_cases.backup.list_backups import ListBackups
from flux_core.use_cases.backup.restore_backup import RestoreBackup


def _make_test_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "sqlite" / "test.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello')")
    conn.commit()
    conn.close()
    return db_path


def _make_test_zvec(tmp_path: Path) -> str:
    zvec_path = str(tmp_path / "zvec")
    os.makedirs(zvec_path, exist_ok=True)
    coll_dir = Path(zvec_path) / "transaction_embeddings"
    coll_dir.mkdir()
    (coll_dir / "data.bin").write_bytes(b"fake-vector-data")
    return zvec_path


def _mock_db(db_path: str):
    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)
    return db


async def test_create_backup_local(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = _mock_db(db_path)
    local_provider = AsyncMock()

    # Capture zip contents during upload (before temp dir cleanup)
    captured_names: list[str] = []
    saved_zip = tmp_path / "captured.zip"

    async def capture_upload(file_path, key):
        import shutil

        shutil.copy2(file_path, saved_zip)
        with zipfile.ZipFile(file_path) as zf:
            captured_names.extend(zf.namelist())
        return key

    local_provider.upload.side_effect = capture_upload

    uc = CreateBackup(db=db, zvec_path=zvec_path, local_provider=local_provider, s3_provider=None)
    result = await uc.execute(storage="local")

    assert result.filename.startswith("flux-backup-")
    assert result.filename.endswith(".zip")
    local_provider.upload.assert_called_once()
    # Verify the uploaded zip contains both sqlite and zvec data
    assert any("flux.db" in n for n in captured_names)
    assert any("zvec/" in n for n in captured_names)


async def test_create_backup_s3(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = _mock_db(db_path)
    s3_provider = AsyncMock()
    s3_provider.upload.return_value = "backups/flux-backup-test.zip"

    uc = CreateBackup(db=db, zvec_path=zvec_path, local_provider=None, s3_provider=s3_provider)
    result = await uc.execute(storage="s3")

    assert result.storage == "s3"
    s3_provider.upload.assert_called_once()


async def test_create_backup_both(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = _mock_db(db_path)
    local_provider = AsyncMock()
    local_provider.upload.return_value = "flux-backup-test.zip"
    s3_provider = AsyncMock()
    s3_provider.upload.return_value = "backups/flux-backup-test.zip"

    uc = CreateBackup(
        db=db, zvec_path=zvec_path, local_provider=local_provider, s3_provider=s3_provider,
    )
    await uc.execute(storage="both")

    local_provider.upload.assert_called_once()
    s3_provider.upload.assert_called_once()


async def test_create_backup_applies_retention(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = _mock_db(db_path)
    local_provider = AsyncMock()
    local_provider.upload.return_value = "new-backup.zip"
    # Simulate 10 existing backups
    local_provider.list_backups.return_value = [
        BackupMetadata(
            id=f"id-{i}",
            filename=f"backup-{i}.zip",
            size_bytes=1024,
            created_at=datetime(2026, 3, 7, tzinfo=UTC),
            storage="local",
        )
        for i in range(10)
    ]

    uc = CreateBackup(
        db=db,
        zvec_path=zvec_path,
        local_provider=local_provider,
        local_retention=3,
    )
    await uc.execute(storage="local")

    # Should have deleted backups beyond retention (10 - 3 = 7 deletions)
    assert local_provider.delete.call_count == 7


async def test_create_backup_no_provider_raises(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    db = _mock_db(db_path)

    uc = CreateBackup(db=db, zvec_path=zvec_path, local_provider=None, s3_provider=None)
    with pytest.raises(ValueError, match="No storage provider"):
        await uc.execute(storage="s3")


# ---------------------------------------------------------------------------
# ListBackups tests
# ---------------------------------------------------------------------------


def _make_meta(filename: str, storage: str = "local") -> BackupMetadata:
    return BackupMetadata(
        id="test-id",
        filename=filename,
        size_bytes=1024,
        created_at=datetime(2026, 3, 7, tzinfo=UTC),
        storage=storage,
        local_path=f"/data/backups/{filename}" if storage == "local" else None,
        s3_key=f"backups/{filename}" if storage == "s3" else None,
    )


async def test_list_backups_combined():
    local = AsyncMock()
    local.list_backups.return_value = [_make_meta("backup-1.zip", "local")]
    s3 = AsyncMock()
    s3.list_backups.return_value = [_make_meta("backup-2.zip", "s3")]
    uc = ListBackups(local_provider=local, s3_provider=s3)
    result = await uc.execute()
    assert len(result) == 2


async def test_list_backups_local_only():
    local = AsyncMock()
    local.list_backups.return_value = [_make_meta("backup-1.zip")]
    uc = ListBackups(local_provider=local, s3_provider=None)
    result = await uc.execute()
    assert len(result) == 1


async def test_list_backups_no_providers():
    uc = ListBackups(local_provider=None, s3_provider=None)
    result = await uc.execute()
    assert result == []


# ---------------------------------------------------------------------------
# DeleteBackup tests
# ---------------------------------------------------------------------------
async def test_delete_backup_local():
    local = AsyncMock()
    uc = DeleteBackup(local_provider=local, s3_provider=None)
    await uc.execute("backup-1.zip", storage="local")
    local.delete.assert_called_once_with("backup-1.zip")


async def test_delete_backup_s3():
    s3 = AsyncMock()
    uc = DeleteBackup(local_provider=None, s3_provider=s3)
    await uc.execute("backups/backup-1.zip", storage="s3")
    s3.delete.assert_called_once_with("backups/backup-1.zip")


# ---------------------------------------------------------------------------
# RestoreBackup tests
# ---------------------------------------------------------------------------


def _make_valid_backup_zip(tmp_path: Path) -> Path:
    """Create a valid backup zip with SQLite DB and zvec directory."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_path / "restore-test.zip"
    db_path = tmp_path / "backup-db.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.execute("INSERT INTO test VALUES (42)")
    conn.commit()
    conn.close()

    zvec_dir = tmp_path / "backup-zvec"
    zvec_dir.mkdir()
    (zvec_dir / "test_collection").mkdir()
    (zvec_dir / "test_collection" / "data.bin").write_bytes(b"vectors")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(db_path, "flux.db")
        for f in zvec_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f"zvec/{f.relative_to(zvec_dir)}")
    return zip_path


async def test_restore_from_file(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    backup_zip = _make_valid_backup_zip(tmp_path / "backup-source")

    db = _mock_db(db_path)
    db.disconnect = MagicMock()
    db.connect = MagicMock()

    create_backup = AsyncMock()
    create_backup.execute.return_value = _make_meta("auto-safety.zip")

    uc = RestoreBackup(db=db, zvec_path=zvec_path, create_backup=create_backup)
    await uc.execute(file_path=backup_zip)

    create_backup.execute.assert_called_once()
    db.disconnect.assert_called_once()
    db.connect.assert_called_once()


async def test_restore_from_s3(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    backup_zip = _make_valid_backup_zip(tmp_path / "s3-source")

    db = _mock_db(db_path)
    db.disconnect = MagicMock()
    db.connect = MagicMock()

    s3_provider = AsyncMock()
    s3_provider.download.return_value = backup_zip

    create_backup = AsyncMock()
    create_backup.execute.return_value = _make_meta("auto-safety.zip")

    uc = RestoreBackup(
        db=db, zvec_path=zvec_path, create_backup=create_backup, s3_provider=s3_provider,
    )
    await uc.execute(s3_key="backups/test.zip")

    s3_provider.download.assert_called_once()
    create_backup.execute.assert_called_once()


async def test_restore_no_args_raises(tmp_path):
    db = MagicMock()
    create_backup = AsyncMock()
    uc = RestoreBackup(db=db, zvec_path="/tmp", create_backup=create_backup)
    with pytest.raises(ValueError, match="Provide either"):
        await uc.execute()
