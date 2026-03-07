"""Tests for backup use cases."""
import os
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from flux_core.use_cases.backup.create_backup import CreateBackup


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
    result = await uc.execute(storage="both")

    local_provider.upload.assert_called_once()
    s3_provider.upload.assert_called_once()


async def test_create_backup_no_provider_raises(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    db = _mock_db(db_path)

    uc = CreateBackup(db=db, zvec_path=zvec_path, local_provider=None, s3_provider=None)
    with pytest.raises(ValueError, match="No storage provider"):
        await uc.execute(storage="s3")
