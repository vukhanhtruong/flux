# Backup & Restore Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full-system backup/restore with local + S3 storage, accessible via API, MCP tools, Telegram bot, and Web UI.

**Architecture:** New `backup` domain in core with Use Cases, a `BackupStorageProvider` protocol with local/S3 implementations, Fernet encryption for sensitive config via `FLUX_SECRET_KEY` env var. Each interface (API, MCP, Bot, Web UI) is a thin adapter. SQLite `connection.backup()` for consistent snapshots. `.zip` archive format.

**Tech Stack:** Python `cryptography` (Fernet), `boto3` (S3), `zipfile` (stdlib), React + TypeScript (Web UI tab)

---

## Phase 1: Core Infrastructure

### Task 1: Add dependencies (`cryptography`, `boto3`)

**Files:**
- Modify: `packages/core/pyproject.toml`
- Modify: `packages/api-server/pyproject.toml`

**Step 1: Add optional dependency groups to core**

In `packages/core/pyproject.toml`, add to `[project.optional-dependencies]`:

```toml
backup = [
    "cryptography>=43.0",
    "boto3>=1.35",
]
```

**Step 2: Add backup extra to api-server**

In `packages/api-server/pyproject.toml`, change dependencies:

```toml
dependencies = [
    "flux-core[backup]",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
]
```

**Step 3: Install and verify**

Run: `cd packages/core && pip install -e ".[backup,dev]"`
Expected: SUCCESS — cryptography and boto3 installed

Run: `python -c "from cryptography.fernet import Fernet; print('ok')"`
Expected: `ok`

**Step 4: Commit**

```bash
git add packages/core/pyproject.toml packages/api-server/pyproject.toml
git commit -m "chore: add cryptography and boto3 as optional backup dependencies"
```

---

### Task 2: SQLite migration — `system_config` table

**Files:**
- Create: `packages/core/src/flux_core/sqlite/migrations/002_system_config.sql`
- Test: `packages/core/tests/test_repositories/test_system_config_repo.py`

**Step 1: Write the migration SQL**

Create `packages/core/src/flux_core/sqlite/migrations/002_system_config.sql`:

```sql
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Step 2: Verify migration runs**

Run:
```python
python -c "
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
import tempfile, os
db = Database(os.path.join(tempfile.mkdtemp(), 'test.db'))
db.connect()
migrate(db)
row = db.fetchone(\"SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'\")
assert row is not None, 'table not created'
print('migration ok')
db.disconnect()
"
```
Expected: `migration ok`

**Step 3: Commit**

```bash
git add packages/core/src/flux_core/sqlite/migrations/002_system_config.sql
git commit -m "feat: add system_config migration for encrypted key-value storage"
```

---

### Task 3: Encryption service

**Files:**
- Create: `packages/core/src/flux_core/services/__init__.py`
- Create: `packages/core/src/flux_core/services/encryption.py`
- Test: `packages/core/tests/test_services/test_encryption.py`
- Create: `packages/core/tests/test_services/__init__.py`

**Step 1: Write the failing test**

Create `packages/core/tests/test_services/__init__.py` (empty) and `test_encryption.py`:

```python
"""Tests for encryption service."""
import os
from unittest.mock import patch

import pytest

from flux_core.services.encryption import EncryptionService


def test_encrypt_decrypt_roundtrip():
    svc = EncryptionService("test-secret-key-123")
    plaintext = "my-s3-secret-access-key"
    encrypted = svc.encrypt(plaintext)
    assert encrypted != plaintext
    assert svc.decrypt(encrypted) == plaintext


def test_different_keys_cannot_decrypt():
    svc1 = EncryptionService("key-one")
    svc2 = EncryptionService("key-two")
    encrypted = svc1.encrypt("secret")
    with pytest.raises(Exception):
        svc2.decrypt(encrypted)


def test_encrypt_returns_different_ciphertext_each_time():
    svc = EncryptionService("test-key")
    e1 = svc.encrypt("same-value")
    e2 = svc.encrypt("same-value")
    # Fernet includes a timestamp + random IV, so ciphertexts differ
    assert e1 != e2


def test_from_env(monkeypatch):
    monkeypatch.setenv("FLUX_SECRET_KEY", "my-env-secret")
    svc = EncryptionService.from_env()
    assert svc.decrypt(svc.encrypt("test")) == "test"


def test_from_env_missing_key(monkeypatch):
    monkeypatch.delenv("FLUX_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="FLUX_SECRET_KEY"):
        EncryptionService.from_env()
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_services/test_encryption.py -v`
Expected: FAIL — module not found

**Step 3: Write implementation**

Create `packages/core/src/flux_core/services/__init__.py` (empty).

Create `packages/core/src/flux_core/services/encryption.py`:

```python
"""Fernet encryption service for sensitive config values."""
from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class EncryptionService:
    """Encrypt/decrypt strings using a user-provided secret key."""

    # Fixed salt — acceptable because the secret key itself provides entropy.
    # Changing this would invalidate all existing encrypted values.
    _SALT = b"flux-finance-config-v1"

    def __init__(self, secret_key: str):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._SALT,
            iterations=480_000,
        )
        derived = kdf.derive(secret_key.encode())
        self._fernet = Fernet(base64.urlsafe_b64encode(derived))

    @classmethod
    def from_env(cls) -> EncryptionService:
        key = os.getenv("FLUX_SECRET_KEY")
        if not key:
            raise ValueError(
                "FLUX_SECRET_KEY environment variable is required for encryption. "
                "Set it to a strong, unique secret string."
            )
        return cls(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
```

**Step 4: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_services/test_encryption.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/services/ packages/core/tests/test_services/
git commit -m "feat: add EncryptionService with Fernet + PBKDF2 for sensitive config"
```

---

### Task 4: SystemConfig repository

**Files:**
- Create: `packages/core/src/flux_core/repositories/system_config_repo.py`
- Create: `packages/core/src/flux_core/sqlite/system_config_repo.py`
- Test: `packages/core/tests/test_repositories/test_system_config_repo.py`

**Step 1: Write the failing test**

Create `packages/core/tests/test_repositories/test_system_config_repo.py`:

```python
"""Tests for SystemConfig repository."""
import sqlite3
import tempfile
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

    # Verify it's stored encrypted in DB
    row = db.fetchone("SELECT value, encrypted FROM system_config WHERE key = ?", ("s3_secret_key",))
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
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_repositories/test_system_config_repo.py -v`
Expected: FAIL — module not found

**Step 3: Write the Protocol interface**

Create `packages/core/src/flux_core/repositories/system_config_repo.py`:

```python
"""SystemConfig repository interface."""
from __future__ import annotations

from typing import Protocol


class SystemConfigRepository(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, *, encrypted: bool = False) -> None: ...
    def delete(self, key: str) -> None: ...
    def get_all(self) -> dict[str, str]: ...
    def get_by_prefix(self, prefix: str) -> dict[str, str]: ...
```

**Step 4: Write the SQLite implementation**

Create `packages/core/src/flux_core/sqlite/system_config_repo.py`:

```python
"""SQLite implementation of SystemConfig repository."""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_core.services.encryption import EncryptionService


class SqliteSystemConfigRepository:
    def __init__(self, conn: sqlite3.Connection, encryption: EncryptionService):
        self._conn = conn
        self._enc = encryption

    def get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value, encrypted FROM system_config WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        if row["encrypted"]:
            return self._enc.decrypt(row["value"])
        return row["value"]

    def set(self, key: str, value: str, *, encrypted: bool = False) -> None:
        stored_value = self._enc.encrypt(value) if encrypted else value
        self._conn.execute(
            "INSERT INTO system_config (key, value, encrypted, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "encrypted = excluded.encrypted, updated_at = datetime('now')",
            (key, stored_value, int(encrypted)),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM system_config WHERE key = ?", (key,))
        self._conn.commit()

    def get_all(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value, encrypted FROM system_config").fetchall()
        result = {}
        for row in rows:
            if row["encrypted"]:
                result[row["key"]] = self._enc.decrypt(row["value"])
            else:
                result[row["key"]] = row["value"]
        return result

    def get_by_prefix(self, prefix: str) -> dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value, encrypted FROM system_config WHERE key LIKE ?",
            (prefix + "%",),
        ).fetchall()
        result = {}
        for row in rows:
            if row["encrypted"]:
                result[row["key"]] = self._enc.decrypt(row["value"])
            else:
                result[row["key"]] = row["value"]
        return result
```

**Step 5: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_repositories/test_system_config_repo.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add packages/core/src/flux_core/repositories/system_config_repo.py \
       packages/core/src/flux_core/sqlite/system_config_repo.py \
       packages/core/tests/test_repositories/test_system_config_repo.py
git commit -m "feat: add SystemConfig repository with encrypted value support"
```

---

### Task 5: BackupMetadata model

**Files:**
- Create: `packages/core/src/flux_core/models/backup.py`
- Test: `packages/core/tests/test_models/test_backup.py`

**Step 1: Write the failing test**

Create `packages/core/tests/test_models/test_backup.py`:

```python
"""Tests for BackupMetadata model."""
from datetime import datetime, UTC

from flux_core.models.backup import BackupMetadata


def test_create_local_backup_metadata():
    meta = BackupMetadata(
        id="abc-123",
        filename="flux-backup-2026-03-07T020000.zip",
        size_bytes=1024000,
        created_at=datetime(2026, 3, 7, 2, 0, 0, tzinfo=UTC),
        storage="local",
        local_path="/data/backups/flux-backup-2026-03-07T020000.zip",
    )
    assert meta.storage == "local"
    assert meta.s3_key is None
    assert meta.local_path is not None


def test_create_s3_backup_metadata():
    meta = BackupMetadata(
        id="def-456",
        filename="flux-backup-2026-03-07T020000.zip",
        size_bytes=1024000,
        created_at=datetime(2026, 3, 7, 2, 0, 0, tzinfo=UTC),
        storage="s3",
        s3_key="backups/flux-backup-2026-03-07T020000.zip",
    )
    assert meta.storage == "s3"
    assert meta.s3_key is not None
    assert meta.local_path is None
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_models/test_backup.py -v`
Expected: FAIL

**Step 3: Write implementation**

Create `packages/core/src/flux_core/models/backup.py`:

```python
"""Backup metadata model."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BackupMetadata(BaseModel):
    id: str
    filename: str
    size_bytes: int
    created_at: datetime
    storage: Literal["local", "s3"]
    s3_key: str | None = None
    local_path: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_models/test_backup.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/models/backup.py packages/core/tests/test_models/test_backup.py
git commit -m "feat: add BackupMetadata Pydantic model"
```

---

### Task 6: Storage Provider protocol + LocalStorageProvider

**Files:**
- Create: `packages/core/src/flux_core/services/storage/__init__.py`
- Create: `packages/core/src/flux_core/services/storage/protocol.py`
- Create: `packages/core/src/flux_core/services/storage/local.py`
- Test: `packages/core/tests/test_services/test_local_storage.py`

**Step 1: Write the failing test**

Create `packages/core/tests/test_services/test_local_storage.py`:

```python
"""Tests for LocalStorageProvider."""
import zipfile
from pathlib import Path

from flux_core.services.storage.local import LocalStorageProvider


def _make_zip(tmp_path: Path, name: str = "test-backup.zip") -> Path:
    zip_path = tmp_path / name
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.txt", "hello")
    return zip_path


async def test_upload_copies_file(tmp_path):
    backup_dir = tmp_path / "backups"
    provider = LocalStorageProvider(str(backup_dir))
    zip_path = _make_zip(tmp_path)

    key = await provider.upload(zip_path, "test-backup.zip")

    assert key == "test-backup.zip"
    assert (backup_dir / "test-backup.zip").exists()


async def test_list_backups(tmp_path):
    backup_dir = tmp_path / "backups"
    provider = LocalStorageProvider(str(backup_dir))

    # Upload two backups
    zip1 = _make_zip(tmp_path, "flux-backup-2026-03-07T010000.zip")
    zip2 = _make_zip(tmp_path, "flux-backup-2026-03-07T020000.zip")
    await provider.upload(zip1, "flux-backup-2026-03-07T010000.zip")
    await provider.upload(zip2, "flux-backup-2026-03-07T020000.zip")

    backups = await provider.list_backups()
    assert len(backups) == 2
    assert all(b.storage == "local" for b in backups)


async def test_download(tmp_path):
    backup_dir = tmp_path / "backups"
    provider = LocalStorageProvider(str(backup_dir))
    zip_path = _make_zip(tmp_path)
    await provider.upload(zip_path, "test-backup.zip")

    dest_dir = tmp_path / "downloads"
    result = await provider.download("test-backup.zip", dest_dir)
    assert result.exists()
    assert result.name == "test-backup.zip"


async def test_delete(tmp_path):
    backup_dir = tmp_path / "backups"
    provider = LocalStorageProvider(str(backup_dir))
    zip_path = _make_zip(tmp_path)
    await provider.upload(zip_path, "test-backup.zip")

    await provider.delete("test-backup.zip")
    backups = await provider.list_backups()
    assert len(backups) == 0


async def test_list_empty(tmp_path):
    provider = LocalStorageProvider(str(tmp_path / "empty"))
    backups = await provider.list_backups()
    assert backups == []
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_services/test_local_storage.py -v`
Expected: FAIL

**Step 3: Write Protocol**

Create `packages/core/src/flux_core/services/storage/__init__.py` (empty).

Create `packages/core/src/flux_core/services/storage/protocol.py`:

```python
"""Backup storage provider protocol."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from flux_core.models.backup import BackupMetadata


class BackupStorageProvider(Protocol):
    async def upload(self, file_path: Path, key: str) -> str: ...
    async def download(self, key: str, dest: Path) -> Path: ...
    async def list_backups(self) -> list[BackupMetadata]: ...
    async def delete(self, key: str) -> None: ...
```

**Step 4: Write LocalStorageProvider**

Create `packages/core/src/flux_core/services/storage/local.py`:

```python
"""Local filesystem backup storage provider."""
from __future__ import annotations

import shutil
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from flux_core.models.backup import BackupMetadata


class LocalStorageProvider:
    def __init__(self, backup_dir: str):
        self._dir = Path(backup_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_path: Path, key: str) -> str:
        dest = self._dir / key
        shutil.copy2(file_path, dest)
        return key

    async def download(self, key: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        src = self._dir / key
        target = dest / key
        shutil.copy2(src, target)
        return target

    async def list_backups(self) -> list[BackupMetadata]:
        if not self._dir.exists():
            return []
        backups = []
        for f in sorted(self._dir.glob("*.zip"), reverse=True):
            stat = f.stat()
            backups.append(
                BackupMetadata(
                    id=str(uuid4()),
                    filename=f.name,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    storage="local",
                    local_path=str(f),
                )
            )
        return backups

    async def delete(self, key: str) -> None:
        path = self._dir / key
        if path.exists():
            path.unlink()
```

**Step 5: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_services/test_local_storage.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add packages/core/src/flux_core/services/storage/ packages/core/tests/test_services/test_local_storage.py
git commit -m "feat: add BackupStorageProvider protocol and LocalStorageProvider"
```

---

### Task 7: S3StorageProvider

**Files:**
- Create: `packages/core/src/flux_core/services/storage/s3.py`
- Test: `packages/core/tests/test_services/test_s3_storage.py`

**Step 1: Write the failing test**

Create `packages/core/tests/test_services/test_s3_storage.py`:

```python
"""Tests for S3StorageProvider (mocked boto3)."""
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime, UTC

from flux_core.services.storage.s3 import S3StorageProvider


def _make_zip(tmp_path: Path, name: str = "test-backup.zip") -> Path:
    zip_path = tmp_path / name
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.txt", "hello")
    return zip_path


@patch("flux_core.services.storage.s3.boto3")
async def test_upload(mock_boto3, tmp_path):
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    provider = S3StorageProvider(
        endpoint="https://r2.example.com",
        access_key="key",
        secret_key="secret",
        bucket="my-bucket",
    )
    zip_path = _make_zip(tmp_path)
    key = await provider.upload(zip_path, "test-backup.zip")

    assert key == "backups/test-backup.zip"
    mock_client.upload_file.assert_called_once()


@patch("flux_core.services.storage.s3.boto3")
async def test_download(mock_boto3, tmp_path):
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    provider = S3StorageProvider(
        endpoint="https://r2.example.com",
        access_key="key",
        secret_key="secret",
        bucket="my-bucket",
    )
    dest = tmp_path / "downloads"
    result = await provider.download("backups/test-backup.zip", dest)

    assert result == dest / "test-backup.zip"
    mock_client.download_file.assert_called_once()


@patch("flux_core.services.storage.s3.boto3")
async def test_list_backups(mock_boto3):
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "backups/flux-backup-2026-03-07T020000.zip",
                "Size": 1024,
                "LastModified": datetime(2026, 3, 7, 2, 0, 0, tzinfo=UTC),
            }
        ]
    }

    provider = S3StorageProvider(
        endpoint="https://r2.example.com",
        access_key="key",
        secret_key="secret",
        bucket="my-bucket",
    )
    backups = await provider.list_backups()

    assert len(backups) == 1
    assert backups[0].storage == "s3"
    assert backups[0].filename == "flux-backup-2026-03-07T020000.zip"


@patch("flux_core.services.storage.s3.boto3")
async def test_list_backups_empty(mock_boto3):
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    mock_client.list_objects_v2.return_value = {}

    provider = S3StorageProvider(
        endpoint="https://r2.example.com",
        access_key="key",
        secret_key="secret",
        bucket="my-bucket",
    )
    backups = await provider.list_backups()
    assert backups == []


@patch("flux_core.services.storage.s3.boto3")
async def test_delete(mock_boto3):
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    provider = S3StorageProvider(
        endpoint="https://r2.example.com",
        access_key="key",
        secret_key="secret",
        bucket="my-bucket",
    )
    await provider.delete("backups/test-backup.zip")

    mock_client.delete_object.assert_called_once_with(
        Bucket="my-bucket", Key="backups/test-backup.zip"
    )
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_services/test_s3_storage.py -v`
Expected: FAIL

**Step 3: Write implementation**

Create `packages/core/src/flux_core/services/storage/s3.py`:

```python
"""S3-compatible backup storage provider."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import boto3

from flux_core.models.backup import BackupMetadata


class S3StorageProvider:
    _PREFIX = "backups/"

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "auto",
    ):
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    async def upload(self, file_path: Path, key: str) -> str:
        s3_key = f"{self._PREFIX}{key}"
        self._client.upload_file(str(file_path), self._bucket, s3_key)
        return s3_key

    async def download(self, key: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        filename = key.split("/")[-1]
        target = dest / filename
        self._client.download_file(self._bucket, key, str(target))
        return target

    async def list_backups(self) -> list[BackupMetadata]:
        response = self._client.list_objects_v2(
            Bucket=self._bucket, Prefix=self._PREFIX
        )
        contents = response.get("Contents", [])
        backups = []
        for obj in contents:
            filename = obj["Key"].split("/")[-1]
            if not filename.endswith(".zip"):
                continue
            backups.append(
                BackupMetadata(
                    id=str(uuid4()),
                    filename=filename,
                    size_bytes=obj["Size"],
                    created_at=obj["LastModified"],
                    storage="s3",
                    s3_key=obj["Key"],
                )
            )
        return sorted(backups, key=lambda b: b.created_at, reverse=True)

    async def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
```

**Step 4: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_services/test_s3_storage.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/services/storage/s3.py packages/core/tests/test_services/test_s3_storage.py
git commit -m "feat: add S3StorageProvider for S3-compatible backup storage"
```

---

## Phase 2: Core Use Cases

### Task 8: CreateBackup use case

**Files:**
- Create: `packages/core/src/flux_core/use_cases/backup/__init__.py`
- Create: `packages/core/src/flux_core/use_cases/backup/create_backup.py`
- Test: `packages/core/tests/test_use_cases/test_backup.py`

**Step 1: Write the failing test**

Create `packages/core/tests/test_use_cases/test_backup.py`:

```python
"""Tests for backup use cases."""
import os
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    # Create a fake collection directory with a file
    coll_dir = Path(zvec_path) / "transaction_embeddings"
    coll_dir.mkdir()
    (coll_dir / "data.bin").write_bytes(b"fake-vector-data")
    return zvec_path


async def test_create_backup_local(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    backup_dir = str(tmp_path / "backups")

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)

    local_provider = AsyncMock()
    local_provider.upload.return_value = "flux-backup-test.zip"

    uc = CreateBackup(
        db=db,
        zvec_path=zvec_path,
        local_provider=local_provider,
        s3_provider=None,
    )
    result = await uc.execute(storage="local")

    assert result.filename.startswith("flux-backup-")
    assert result.filename.endswith(".zip")
    local_provider.upload.assert_called_once()
    # Verify the uploaded zip contains both sqlite and zvec data
    uploaded_path = local_provider.upload.call_args[0][0]
    assert zipfile.is_zipfile(uploaded_path)
    with zipfile.ZipFile(uploaded_path) as zf:
        names = zf.namelist()
        assert any("flux.db" in n for n in names)
        assert any("zvec/" in n for n in names)


async def test_create_backup_s3(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)

    s3_provider = AsyncMock()
    s3_provider.upload.return_value = "backups/flux-backup-test.zip"

    uc = CreateBackup(
        db=db,
        zvec_path=zvec_path,
        local_provider=None,
        s3_provider=s3_provider,
    )
    result = await uc.execute(storage="s3")

    assert result.storage == "s3"
    s3_provider.upload.assert_called_once()


async def test_create_backup_both(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)

    local_provider = AsyncMock()
    local_provider.upload.return_value = "flux-backup-test.zip"
    s3_provider = AsyncMock()
    s3_provider.upload.return_value = "backups/flux-backup-test.zip"

    uc = CreateBackup(
        db=db,
        zvec_path=zvec_path,
        local_provider=local_provider,
        s3_provider=s3_provider,
    )
    result = await uc.execute(storage="both")

    local_provider.upload.assert_called_once()
    s3_provider.upload.assert_called_once()


async def test_create_backup_no_provider_raises(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)

    uc = CreateBackup(db=db, zvec_path=zvec_path, local_provider=None, s3_provider=None)

    import pytest
    with pytest.raises(ValueError, match="No storage provider"):
        await uc.execute(storage="s3")
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v`
Expected: FAIL

**Step 3: Write implementation**

Create `packages/core/src/flux_core/use_cases/backup/__init__.py`:

```python
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.list_backups import ListBackups
from flux_core.use_cases.backup.delete_backup import DeleteBackup
```

Create `packages/core/src/flux_core/use_cases/backup/create_backup.py`:

```python
"""CreateBackup use case — snapshot SQLite + zvec into a .zip archive."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import structlog

from flux_core.models.backup import BackupMetadata

if TYPE_CHECKING:
    from flux_core.services.storage.local import LocalStorageProvider
    from flux_core.services.storage.s3 import S3StorageProvider
    from flux_core.sqlite.database import Database

logger = structlog.get_logger(__name__)


class CreateBackup:
    def __init__(
        self,
        db: Database,
        zvec_path: str,
        local_provider: LocalStorageProvider | None = None,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._db = db
        self._zvec_path = zvec_path
        self._local = local_provider
        self._s3 = s3_provider

    async def execute(
        self,
        storage: Literal["local", "s3", "both"] = "local",
    ) -> BackupMetadata:
        provider = self._resolve_provider(storage)

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S")
        filename = f"flux-backup-{timestamp}.zip"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            zip_path = tmp / filename

            # 1. SQLite backup via connection.backup() — consistent snapshot
            db_backup = tmp / "flux.db"
            src_conn = self._db.connection()
            dst_conn = sqlite3.connect(str(db_backup))
            src_conn.backup(dst_conn)
            dst_conn.close()
            logger.info("SQLite backup snapshot created", path=str(db_backup))

            # 2. Copy zvec directory
            zvec_src = Path(self._zvec_path)
            zvec_dst = tmp / "zvec"
            if zvec_src.exists():
                shutil.copytree(zvec_src, zvec_dst)
                logger.info("zvec directory copied", src=str(zvec_src))

            # 3. Create zip
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_backup, "flux.db")
                if zvec_dst.exists():
                    for f in zvec_dst.rglob("*"):
                        if f.is_file():
                            arcname = f"zvec/{f.relative_to(zvec_dst)}"
                            zf.write(f, arcname)
            logger.info("Backup zip created", filename=filename, size=zip_path.stat().st_size)

            # 4. Upload to storage(s)
            result_meta = None
            if storage in ("local", "both") and self._local:
                key = await self._local.upload(zip_path, filename)
                result_meta = BackupMetadata(
                    id=timestamp,
                    filename=filename,
                    size_bytes=zip_path.stat().st_size,
                    created_at=datetime.now(UTC),
                    storage="local",
                    local_path=key,
                )
            if storage in ("s3", "both") and self._s3:
                key = await self._s3.upload(zip_path, filename)
                result_meta = BackupMetadata(
                    id=timestamp,
                    filename=filename,
                    size_bytes=zip_path.stat().st_size,
                    created_at=datetime.now(UTC),
                    storage="s3",
                    s3_key=key,
                )

        return result_meta

    def _resolve_provider(self, storage: str):
        if storage == "local" and not self._local:
            raise ValueError("No storage provider available for 'local'")
        if storage == "s3" and not self._s3:
            raise ValueError("No storage provider available for 's3'")
        if storage == "both" and not (self._local or self._s3):
            raise ValueError("No storage provider available")
```

**Step 4: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/use_cases/backup/ packages/core/tests/test_use_cases/test_backup.py
git commit -m "feat: add CreateBackup use case with SQLite backup() + zvec copy"
```

---

### Task 9: ListBackups and DeleteBackup use cases

**Files:**
- Create: `packages/core/src/flux_core/use_cases/backup/list_backups.py`
- Create: `packages/core/src/flux_core/use_cases/backup/delete_backup.py`
- Test: append to `packages/core/tests/test_use_cases/test_backup.py`

**Step 1: Write the failing tests**

Append to `packages/core/tests/test_use_cases/test_backup.py`:

```python
from flux_core.use_cases.backup.list_backups import ListBackups
from flux_core.use_cases.backup.delete_backup import DeleteBackup
from flux_core.models.backup import BackupMetadata
from datetime import datetime, UTC


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
```

**Step 2: Run test to verify new tests fail**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v -k "list_or_delete"`
Expected: FAIL

**Step 3: Write implementations**

Create `packages/core/src/flux_core/use_cases/backup/list_backups.py`:

```python
"""ListBackups use case — list backups from local + S3."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flux_core.models.backup import BackupMetadata

if TYPE_CHECKING:
    from flux_core.services.storage.local import LocalStorageProvider
    from flux_core.services.storage.s3 import S3StorageProvider


class ListBackups:
    def __init__(
        self,
        local_provider: LocalStorageProvider | None = None,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._local = local_provider
        self._s3 = s3_provider

    async def execute(self) -> list[BackupMetadata]:
        backups: list[BackupMetadata] = []
        if self._local:
            backups.extend(await self._local.list_backups())
        if self._s3:
            backups.extend(await self._s3.list_backups())
        return sorted(backups, key=lambda b: b.created_at, reverse=True)
```

Create `packages/core/src/flux_core/use_cases/backup/delete_backup.py`:

```python
"""DeleteBackup use case — delete a backup from specified storage."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from flux_core.services.storage.local import LocalStorageProvider
    from flux_core.services.storage.s3 import S3StorageProvider


class DeleteBackup:
    def __init__(
        self,
        local_provider: LocalStorageProvider | None = None,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._local = local_provider
        self._s3 = s3_provider

    async def execute(self, key: str, *, storage: Literal["local", "s3"] = "local") -> None:
        if storage == "local" and self._local:
            await self._local.delete(key)
        elif storage == "s3" and self._s3:
            await self._s3.delete(key)
```

**Step 4: Run all backup tests**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/use_cases/backup/
git commit -m "feat: add ListBackups and DeleteBackup use cases"
```

---

### Task 10: RestoreBackup use case

**Files:**
- Create: `packages/core/src/flux_core/use_cases/backup/restore_backup.py`
- Test: append to `packages/core/tests/test_use_cases/test_backup.py`

**Step 1: Write the failing tests**

Append to `packages/core/tests/test_use_cases/test_backup.py`:

```python
from flux_core.use_cases.backup.restore_backup import RestoreBackup


def _make_valid_backup_zip(tmp_path: Path) -> Path:
    """Create a valid backup zip with SQLite DB and zvec directory."""
    zip_path = tmp_path / "restore-test.zip"
    # Create a real SQLite DB for the backup
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

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)
    db.disconnect = MagicMock()
    db.connect = MagicMock()

    # Mock CreateBackup for auto-backup
    create_backup = AsyncMock()
    create_backup.execute.return_value = _make_meta("auto-safety.zip")

    uc = RestoreBackup(
        db=db,
        zvec_path=zvec_path,
        create_backup=create_backup,
    )
    await uc.execute(file_path=backup_zip)

    # Auto-backup should have been created
    create_backup.execute.assert_called_once()
    # DB should have been reconnected
    db.disconnect.assert_called_once()
    db.connect.assert_called_once()


async def test_restore_from_s3(tmp_path):
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    backup_zip = _make_valid_backup_zip(tmp_path / "s3-source")

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)
    db.disconnect = MagicMock()
    db.connect = MagicMock()

    s3_provider = AsyncMock()
    s3_provider.download.return_value = backup_zip

    create_backup = AsyncMock()
    create_backup.execute.return_value = _make_meta("auto-safety.zip")

    uc = RestoreBackup(
        db=db,
        zvec_path=zvec_path,
        create_backup=create_backup,
        s3_provider=s3_provider,
    )
    await uc.execute(s3_key="backups/test.zip")

    s3_provider.download.assert_called_once()
    create_backup.execute.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py::test_restore_from_file -v`
Expected: FAIL

**Step 3: Write implementation**

Create `packages/core/src/flux_core/use_cases/backup/restore_backup.py`:

```python
"""RestoreBackup use case — auto-backup then replace SQLite + zvec."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from flux_core.services.storage.s3 import S3StorageProvider
    from flux_core.sqlite.database import Database
    from flux_core.use_cases.backup.create_backup import CreateBackup

logger = structlog.get_logger(__name__)


class RestoreBackup:
    def __init__(
        self,
        db: Database,
        zvec_path: str,
        create_backup: CreateBackup,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._db = db
        self._zvec_path = zvec_path
        self._create_backup = create_backup
        self._s3 = s3_provider

    async def execute(
        self,
        *,
        file_path: Path | None = None,
        s3_key: str | None = None,
    ) -> None:
        if not file_path and not s3_key:
            raise ValueError("Provide either file_path or s3_key")

        # 1. Auto-backup current data
        logger.info("Creating safety backup before restore")
        await self._create_backup.execute(storage="local")

        # 2. Get the backup zip
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            if s3_key and self._s3:
                zip_path = await self._s3.download(s3_key, tmp)
            elif file_path:
                zip_path = file_path
            else:
                raise ValueError("S3 provider not configured")

            # 3. Validate zip contents
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                if "flux.db" not in names:
                    raise ValueError("Invalid backup: missing flux.db")

            # 4. Extract to temp
            extract_dir = tmp / "extracted"
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)

            # 5. Validate SQLite integrity
            restored_db = extract_dir / "flux.db"
            test_conn = sqlite3.connect(str(restored_db))
            result = test_conn.execute("PRAGMA integrity_check").fetchone()
            test_conn.close()
            if result[0] != "ok":
                raise ValueError(f"Backup database integrity check failed: {result[0]}")

            # 6. Disconnect, replace, reconnect
            self._db.disconnect()

            # Replace SQLite
            db_path = Path(self._db._path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(restored_db, db_path)
            # Remove WAL/SHM files from old DB
            for suffix in ("-wal", "-shm"):
                wal = db_path.with_name(db_path.name + suffix)
                if wal.exists():
                    wal.unlink()

            # Replace zvec
            restored_zvec = extract_dir / "zvec"
            if restored_zvec.exists():
                zvec_dest = Path(self._zvec_path)
                if zvec_dest.exists():
                    shutil.rmtree(zvec_dest)
                shutil.copytree(restored_zvec, zvec_dest)

            # 7. Reconnect
            self._db.connect()
            logger.info("Restore completed successfully")
```

Update `packages/core/src/flux_core/use_cases/backup/__init__.py`:

```python
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.list_backups import ListBackups
from flux_core.use_cases.backup.delete_backup import DeleteBackup
from flux_core.use_cases.backup.restore_backup import RestoreBackup
```

**Step 4: Run tests**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/use_cases/backup/
git commit -m "feat: add RestoreBackup use case with auto-backup safety and integrity check"
```

---

## Phase 3: API Server

### Task 11: Backup API routes

**Files:**
- Create: `packages/api-server/src/flux_api/routes/backups.py`
- Modify: `packages/api-server/src/flux_api/app.py` (add router)
- Modify: `packages/api-server/src/flux_api/deps.py` (add backup deps)
- Test: `packages/api-server/tests/test_backups.py`

**Step 1: Write the failing test**

Create `packages/api-server/tests/test_backups.py`:

```python
"""Tests for backup API routes."""
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from flux_core.models.backup import BackupMetadata


def _make_meta(filename: str = "flux-backup-test.zip", storage: str = "local"):
    return BackupMetadata(
        id="test-id",
        filename=filename,
        size_bytes=1024,
        created_at=datetime(2026, 3, 7, tzinfo=UTC),
        storage=storage,
        local_path=f"/data/backups/{filename}" if storage == "local" else None,
        s3_key=f"backups/{filename}" if storage == "s3" else None,
    )


@patch("flux_api.routes.backups.get_create_backup_uc")
async def test_create_backup(mock_get_uc):
    from flux_api.app import app
    mock_uc = AsyncMock()
    mock_uc.execute.return_value = _make_meta()
    mock_get_uc.return_value = mock_uc

    client = TestClient(app)
    response = client.post("/backups/?storage=local")
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "flux-backup-test.zip"


@patch("flux_api.routes.backups.get_list_backups_uc")
async def test_list_backups(mock_get_uc):
    from flux_api.app import app
    mock_uc = AsyncMock()
    mock_uc.execute.return_value = [_make_meta()]
    mock_get_uc.return_value = mock_uc

    client = TestClient(app)
    response = client.get("/backups/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@patch("flux_api.routes.backups.get_delete_backup_uc")
async def test_delete_backup(mock_get_uc):
    from flux_api.app import app
    mock_uc = AsyncMock()
    mock_get_uc.return_value = mock_uc

    client = TestClient(app)
    response = client.delete("/backups/test-backup.zip?storage=local")
    assert response.status_code == 204
```

**Step 2: Run test to verify it fails**

Run: `cd packages/api-server && python -m pytest tests/test_backups.py -v`
Expected: FAIL

**Step 3: Add backup dependencies to deps.py**

Add to `packages/api-server/src/flux_api/deps.py`:

```python
import os
from flux_core.services.storage.local import LocalStorageProvider

_local_storage: LocalStorageProvider | None = None
_s3_storage = None


def get_local_storage() -> LocalStorageProvider:
    global _local_storage
    if _local_storage is None:
        backup_dir = os.getenv("BACKUP_LOCAL_DIR", "/data/backups")
        _local_storage = LocalStorageProvider(backup_dir)
    return _local_storage


def get_s3_storage():
    """Get S3 provider if configured via system_config. Returns None if not configured."""
    global _s3_storage
    if _s3_storage is not None:
        return _s3_storage
    try:
        from flux_core.services.encryption import EncryptionService
        from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository
        enc = EncryptionService.from_env()
        db = get_db()
        config_repo = SqliteSystemConfigRepository(db.connection(), enc)
        endpoint = config_repo.get("s3_endpoint")
        bucket = config_repo.get("s3_bucket")
        access_key = config_repo.get("s3_access_key")
        secret_key = config_repo.get("s3_secret_key")
        if all([endpoint, bucket, access_key, secret_key]):
            from flux_core.services.storage.s3 import S3StorageProvider
            region = config_repo.get("s3_region") or "auto"
            _s3_storage = S3StorageProvider(endpoint, access_key, secret_key, bucket, region)
    except (ValueError, ImportError):
        pass
    return _s3_storage
```

**Step 4: Write routes**

Create `packages/api-server/src/flux_api/routes/backups.py`:

```python
"""Backup/restore REST routes."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import FileResponse

from flux_api.deps import get_db, get_local_storage, get_s3_storage
from flux_core.models.backup import BackupMetadata
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.delete_backup import DeleteBackup
from flux_core.use_cases.backup.list_backups import ListBackups
from flux_core.use_cases.backup.restore_backup import RestoreBackup

router = APIRouter(prefix="/backups", tags=["backups"])


def get_create_backup_uc() -> CreateBackup:
    return CreateBackup(
        db=get_db(),
        zvec_path=os.getenv("ZVEC_PATH", "/data/zvec"),
        local_provider=get_local_storage(),
        s3_provider=get_s3_storage(),
    )


def get_list_backups_uc() -> ListBackups:
    return ListBackups(
        local_provider=get_local_storage(),
        s3_provider=get_s3_storage(),
    )


def get_delete_backup_uc() -> DeleteBackup:
    return DeleteBackup(
        local_provider=get_local_storage(),
        s3_provider=get_s3_storage(),
    )


def get_restore_backup_uc() -> RestoreBackup:
    return RestoreBackup(
        db=get_db(),
        zvec_path=os.getenv("ZVEC_PATH", "/data/zvec"),
        create_backup=get_create_backup_uc(),
        s3_provider=get_s3_storage(),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_backup(
    storage: Literal["local", "s3", "both"] = "local",
) -> BackupMetadata:
    uc = get_create_backup_uc()
    return await uc.execute(storage=storage)


@router.get("/")
async def list_backups() -> list[BackupMetadata]:
    uc = get_list_backups_uc()
    return await uc.execute()


@router.get("/{filename}/download")
async def download_backup(filename: str):
    local = get_local_storage()
    file_path = Path(local._dir) / filename
    if not file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Backup not found locally")
    return FileResponse(path=str(file_path), filename=filename, media_type="application/zip")


@router.post("/restore", status_code=status.HTTP_200_OK)
async def restore_backup(
    backup_id: str | None = None,
    s3_key: str | None = None,
    file: UploadFile | None = File(None),
) -> dict:
    uc = get_restore_backup_uc()
    if file:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        await uc.execute(file_path=tmp_path)
        tmp_path.unlink(missing_ok=True)
    elif s3_key:
        await uc.execute(s3_key=s3_key)
    elif backup_id:
        local = get_local_storage()
        file_path = Path(local._dir) / backup_id
        await uc.execute(file_path=file_path)
    else:
        from fastapi import HTTPException
        raise HTTPException(400, "Provide file upload, s3_key, or backup_id")
    return {"status": "restored", "message": "Data restored successfully. Services may need restart."}


@router.delete("/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    key: str,
    storage: Literal["local", "s3"] = "local",
):
    uc = get_delete_backup_uc()
    await uc.execute(key, storage=storage)
```

**Step 5: Register router in app.py**

Add to `packages/api-server/src/flux_api/app.py` after the other imports:

```python
from flux_api.routes.backups import router as backups_router  # noqa: E402

app.include_router(backups_router)
```

**Step 6: Run tests**

Run: `cd packages/api-server && python -m pytest tests/test_backups.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add packages/api-server/src/flux_api/routes/backups.py \
       packages/api-server/src/flux_api/app.py \
       packages/api-server/src/flux_api/deps.py \
       packages/api-server/tests/test_backups.py
git commit -m "feat: add backup/restore REST API endpoints"
```

---

## Phase 4: MCP Server

### Task 12: Backup MCP tools

**Files:**
- Create: `packages/mcp-server/src/flux_mcp/tools/backup_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/server.py` (register tools)
- Test: `packages/mcp-server/tests/test_backup_tools.py`

**Step 1: Write the failing test**

Create `packages/mcp-server/tests/test_backup_tools.py`:

```python
"""Tests for backup MCP tools."""
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from flux_core.models.backup import BackupMetadata


def _make_meta(filename="test.zip", storage="local"):
    return BackupMetadata(
        id="test", filename=filename, size_bytes=1024,
        created_at=datetime(2026, 3, 7, tzinfo=UTC), storage=storage,
    )


@patch("flux_mcp.tools.backup_tools.CreateBackup")
async def test_create_backup_tool(mock_cls):
    mock_cls.return_value.execute = AsyncMock(return_value=_make_meta())

    from flux_mcp.tools.backup_tools import _create_backup_impl
    result = await _create_backup_impl(
        get_db=MagicMock(), zvec_path="/data/zvec",
        get_local_storage=MagicMock(), get_s3_storage=MagicMock(return_value=None),
        storage="local",
    )
    assert result["filename"] == "test.zip"
    assert result["status"] == "success"


@patch("flux_mcp.tools.backup_tools.ListBackups")
async def test_list_backups_tool(mock_cls):
    mock_cls.return_value.execute = AsyncMock(return_value=[_make_meta()])

    from flux_mcp.tools.backup_tools import _list_backups_impl
    result = await _list_backups_impl(
        get_local_storage=MagicMock(), get_s3_storage=MagicMock(return_value=None),
    )
    assert len(result) == 1
```

**Step 2: Run test to verify it fails**

Run: `cd packages/mcp-server && python -m pytest tests/test_backup_tools.py -v`
Expected: FAIL

**Step 3: Write implementation**

Create `packages/mcp-server/src/flux_mcp/tools/backup_tools.py`:

```python
"""Backup/restore MCP tools."""
from __future__ import annotations

import os
from typing import Callable, Literal

from fastmcp import FastMCP

from flux_core.models.backup import BackupMetadata
from flux_core.services.storage.local import LocalStorageProvider
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.list_backups import ListBackups


async def _create_backup_impl(
    get_db, zvec_path, get_local_storage, get_s3_storage, storage="local",
) -> dict:
    uc = CreateBackup(
        db=get_db(), zvec_path=zvec_path,
        local_provider=get_local_storage(), s3_provider=get_s3_storage(),
    )
    result = await uc.execute(storage=storage)
    return {
        "status": "success",
        "filename": result.filename,
        "size_bytes": result.size_bytes,
        "storage": result.storage,
    }


async def _list_backups_impl(get_local_storage, get_s3_storage) -> list[dict]:
    uc = ListBackups(
        local_provider=get_local_storage(), s3_provider=get_s3_storage(),
    )
    backups = await uc.execute()
    return [
        {
            "filename": b.filename,
            "size_bytes": b.size_bytes,
            "created_at": str(b.created_at),
            "storage": b.storage,
        }
        for b in backups
    ]


def register_backup_tools(
    mcp: FastMCP,
    get_db: Callable,
    get_local_storage: Callable,
    get_s3_storage: Callable,
):
    zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")

    @mcp.tool()
    async def create_backup(storage: str = "local") -> dict:
        """Create a backup of all data (SQLite + vector embeddings) as a .zip archive."""
        return await _create_backup_impl(
            get_db, zvec_path, get_local_storage, get_s3_storage, storage,
        )

    @mcp.tool()
    async def list_backups() -> list[dict]:
        """List all available backups from local and S3 storage."""
        return await _list_backups_impl(get_local_storage, get_s3_storage)
```

**Step 4: Register in server.py**

Add to `packages/mcp-server/src/flux_mcp/server.py`:

- Add import: `from flux_mcp.tools.backup_tools import register_backup_tools`
- Add storage helper functions (similar to API deps):

```python
def get_local_storage():
    from flux_core.services.storage.local import LocalStorageProvider
    backup_dir = os.getenv("BACKUP_LOCAL_DIR", "/data/backups")
    return LocalStorageProvider(backup_dir)

def get_s3_storage():
    try:
        from flux_core.services.encryption import EncryptionService
        from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository
        enc = EncryptionService.from_env()
        config_repo = SqliteSystemConfigRepository(get_db().connection(), enc)
        endpoint = config_repo.get("s3_endpoint")
        bucket = config_repo.get("s3_bucket")
        access_key = config_repo.get("s3_access_key")
        secret_key = config_repo.get("s3_secret_key")
        if all([endpoint, bucket, access_key, secret_key]):
            from flux_core.services.storage.s3 import S3StorageProvider
            region = config_repo.get("s3_region") or "auto"
            return S3StorageProvider(endpoint, access_key, secret_key, bucket, region)
    except (ValueError, ImportError):
        pass
    return None
```

- Add registration call:

```python
register_backup_tools(mcp, get_db, get_local_storage, get_s3_storage)
```

**Step 5: Run tests**

Run: `cd packages/mcp-server && python -m pytest tests/test_backup_tools.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add packages/mcp-server/src/flux_mcp/tools/backup_tools.py \
       packages/mcp-server/src/flux_mcp/server.py \
       packages/mcp-server/tests/test_backup_tools.py
git commit -m "feat: add backup/restore MCP tools"
```

---

## Phase 5: Agent Bot

### Task 13: Bot /backup and /restore commands

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/channels/commands.py`
- Modify: `packages/agent-bot/src/flux_bot/channels/telegram.py`
- Test: `packages/agent-bot/tests/test_channels/test_backup_commands.py`

**Step 1: Write the failing test**

Create `packages/agent-bot/tests/test_channels/test_backup_commands.py`:

```python
"""Tests for /backup and /restore bot commands."""
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest


def _mock_update(user_id=12345):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    return update


def _mock_context():
    ctx = MagicMock()
    ctx.user_data = {}
    return ctx


def _mock_profile():
    profile = MagicMock()
    profile.user_id = "tg:12345"
    profile.timezone = "UTC"
    return profile


@patch("flux_bot.channels.commands.CreateBackup")
async def test_cmd_backup_no_s3(mock_create_cls):
    from flux_bot.channels.commands import CommandHandlers

    profile_repo = AsyncMock()
    profile_repo.get_by_platform_id.return_value = _mock_profile()

    cmds = CommandHandlers(
        profile_repo=profile_repo,
        session_repo=AsyncMock(),
        task_repo=AsyncMock(),
    )

    mock_meta = MagicMock()
    mock_meta.filename = "flux-backup-test.zip"
    mock_meta.size_bytes = 1024
    mock_create_cls.return_value.execute = AsyncMock(return_value=mock_meta)

    update = _mock_update()
    ctx = _mock_context()

    # This test validates the handler exists and runs without error
    # Full integration tested via E2E
    with patch.object(cmds, "_get_s3_configured", return_value=False):
        with patch.object(cmds, "_send_backup_as_document", new_callable=AsyncMock):
            await cmds.cmd_backup(update, ctx)

    update.message.reply_text.assert_called()
```

**Step 2: Run test to verify it fails**

Run: `cd packages/agent-bot && python -m pytest tests/test_channels/test_backup_commands.py -v`
Expected: FAIL

**Step 3: Add backup commands to CommandHandlers**

In `packages/agent-bot/src/flux_bot/channels/commands.py`, add to imports:

```python
import os
import tempfile
from pathlib import Path
```

Add these methods to the `CommandHandlers` class:

```python
    # ------------------------------------------------------------------
    # /backup
    # ------------------------------------------------------------------

    def _get_s3_configured(self) -> bool:
        """Check if S3 is configured via system_config."""
        try:
            from flux_core.services.encryption import EncryptionService
            from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository
            from flux_core.sqlite.database import Database
            from flux_core.sqlite.migrations.migrate import migrate
            db_path = os.getenv("DATABASE_PATH", "/data/sqlite/flux.db")
            db = Database(db_path)
            db.connect()
            enc = EncryptionService.from_env()
            repo = SqliteSystemConfigRepository(db.connection(), enc)
            endpoint = repo.get("s3_endpoint")
            bucket = repo.get("s3_bucket")
            db.disconnect()
            return bool(endpoint and bucket)
        except Exception:
            return False

    async def _send_backup_as_document(self, update: Update, zip_path: Path, filename: str):
        """Send backup file via Telegram send_document."""
        with open(zip_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption="Here's your backup file. Keep it safe!",
            )

    async def cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        profile = await self._get_profile(update)
        if profile is None:
            await update.message.reply_text("Please complete setup first with /onboard")
            return

        s3_configured = self._get_s3_configured()
        if s3_configured:
            keyboard = [
                [
                    InlineKeyboardButton("Send to Telegram", callback_data="backup:telegram"),
                    InlineKeyboardButton("Upload to S3", callback_data="backup:s3"),
                ],
            ]
            await update.message.reply_text(
                "Where should I save the backup?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text("Creating backup... This may take a moment.")
            from flux_core.use_cases.backup.create_backup import CreateBackup
            from flux_core.sqlite.database import Database
            from flux_core.sqlite.migrations.migrate import migrate
            from flux_core.services.storage.local import LocalStorageProvider

            db_path = os.getenv("DATABASE_PATH", "/data/sqlite/flux.db")
            zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
            backup_dir = os.getenv("BACKUP_LOCAL_DIR", "/data/backups")
            local = LocalStorageProvider(backup_dir)

            db = Database(db_path)
            db.connect()
            uc = CreateBackup(db=db, zvec_path=zvec_path, local_provider=local)
            meta = await uc.execute(storage="local")
            db.disconnect()

            # Send file via Telegram
            zip_path = Path(local._dir) / meta.filename
            await self._send_backup_as_document(update, zip_path, meta.filename)
            await update.message.reply_text(
                f"Backup created: {meta.filename} ({meta.size_bytes:,} bytes)\n\n"
                "Tip: Configure S3 storage in Web UI Settings for off-site backups."
            )

    async def cmd_restore(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        profile = await self._get_profile(update)
        if profile is None:
            await update.message.reply_text("Please complete setup first with /onboard")
            return

        await update.message.reply_text(
            "To restore, send me a backup .zip file.\n\n"
            "⚠️ This will replace ALL current data. "
            "A safety backup will be created automatically first."
        )
        context.user_data["awaiting_restore"] = True
```

**Step 4: Register commands in telegram.py**

In `packages/agent-bot/src/flux_bot/channels/telegram.py`, add to `start()`:

```python
self._app.add_handler(TelegramCommandHandler("backup", cmds.cmd_backup))
self._app.add_handler(TelegramCommandHandler("restore", cmds.cmd_restore))
```

**Step 5: Update HELP_TEXT**

In commands.py, add to HELP_TEXT:

```python
💾 Backup your data → /backup
🔄 Restore from backup → /restore
```

**Step 6: Run tests**

Run: `cd packages/agent-bot && python -m pytest tests/test_channels/test_backup_commands.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add packages/agent-bot/src/flux_bot/channels/commands.py \
       packages/agent-bot/src/flux_bot/channels/telegram.py \
       packages/agent-bot/tests/test_channels/test_backup_commands.py
git commit -m "feat: add /backup and /restore Telegram bot commands"
```

---

### Task 14: Add backup preference to /onboard flow

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/channels/commands.py`
- Test: update test for onboarding

**Step 1: Add backup preference step to onboard**

In `commands.py`, extend the onboard states:

```python
_OB_CURRENCY, _OB_TIMEZONE, _OB_USERNAME, _OB_BACKUP = range(4)
```

After the username step completes (in `_ob_handle_username` and `_ob_skip_username`), instead of ending the conversation, transition to `_OB_BACKUP`:

Add method:

```python
    async def _send_ob_backup_prompt(self, source) -> None:
        keyboard = [
            [InlineKeyboardButton("Daily", callback_data="ob_backup:daily")],
            [InlineKeyboardButton("Weekly", callback_data="ob_backup:weekly")],
            [InlineKeyboardButton("Never", callback_data="ob_backup:never")],
        ]
        await source.message.reply_text(
            "💾 Auto-backup (4/4)\n\n"
            "How often should I automatically backup your data?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _ob_handle_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        choice = update.callback_query.data.split(":", 1)[1]
        context.user_data["ob_backup"] = choice

        if choice == "never":
            msg = "No auto-backup configured. You can always use /backup manually."
        else:
            msg = f"Auto-backup set to {choice}. You can change this in Settings."
            # TODO: Create scheduled task for backup (Task 15 will implement this)

        await update.callback_query.message.reply_text(
            f"✅ {msg}\n\n" + HELP_TEXT, parse_mode="Markdown"
        )
        return ConversationHandler.END
```

Update `onboard_conversation()` to include the new state:

```python
_OB_BACKUP: [
    CallbackQueryHandler(self._ob_handle_backup, pattern="^ob_backup:"),
],
```

Modify `_ob_handle_username` and `_ob_skip_username` to go to `_OB_BACKUP` instead of `ConversationHandler.END`.

**Step 2: Run tests**

Run: `cd packages/agent-bot && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add packages/agent-bot/src/flux_bot/channels/commands.py
git commit -m "feat: add backup preference step to /onboard flow"
```

---

## Phase 6: Web UI

### Task 15: Data tab in Settings page

**Files:**
- Create: `packages/web-ui/src/pages/settings/DataTab.tsx`
- Modify: `packages/web-ui/src/pages/Settings.tsx`
- Modify: `packages/web-ui/src/lib/api.ts`
- Modify: `packages/web-ui/src/types/index.ts` (add Backup types)

**Step 1: Add backup types**

Add to `packages/web-ui/src/types/index.ts` (or wherever types are defined):

```typescript
export interface BackupMetadata {
  id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
  storage: "local" | "s3";
  s3_key?: string;
  local_path?: string;
}
```

**Step 2: Add API methods**

Add to `packages/web-ui/src/lib/api.ts` in the `ApiClient` class:

```typescript
  // Backups
  async createBackup(storage: string = "local"): Promise<BackupMetadata> {
    const params = new URLSearchParams({ storage });
    return this.request(`/backups/?${params}`, { method: "POST" });
  }

  async listBackups(): Promise<BackupMetadata[]> {
    return this.request("/backups/");
  }

  async deleteBackup(key: string, storage: string = "local"): Promise<void> {
    const params = new URLSearchParams({ storage });
    return this.request(`/backups/${key}?${params}`, { method: "DELETE" });
  }

  async restoreBackup(file?: File, backupId?: string): Promise<{ status: string; message: string }> {
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      const url = `${this.baseUrl}/backups/restore`;
      const response = await fetch(url, { method: "POST", body: formData });
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      return response.json();
    }
    return this.request(`/backups/restore?backup_id=${backupId}`, { method: "POST" });
  }

  getBackupDownloadUrl(filename: string): string {
    return `${this.baseUrl}/backups/${filename}/download`;
  }
```

**Step 3: Create DataTab component**

Create `packages/web-ui/src/pages/settings/DataTab.tsx`:

```tsx
import { useState, useEffect } from "react";
import { Download, Upload, Trash2, HardDrive, Cloud, RefreshCw } from "lucide-react";
import { api } from "../../lib/api";
import type { BackupMetadata } from "../../types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export function DataTab() {
  const [backups, setBackups] = useState<BackupMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadBackups() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listBackups();
      setBackups(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadBackups(); }, []);

  async function handleCreateBackup(storage: string = "local") {
    setCreating(true);
    setError(null);
    try {
      await api.createBackup(storage);
      setMessage("Backup created successfully!");
      await loadBackups();
    } catch (err) {
      setError(String(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(key: string, storage: string) {
    if (!confirm("Delete this backup?")) return;
    try {
      await api.deleteBackup(key, storage);
      await loadBackups();
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleRestore(file?: File, backupId?: string) {
    if (!confirm("This will replace ALL current data. A safety backup will be created first. Continue?")) return;
    setRestoring(true);
    setError(null);
    try {
      const result = await api.restoreBackup(file, backupId);
      setMessage(result.message);
    } catch (err) {
      setError(String(err));
    } finally {
      setRestoring(false);
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleRestore(file);
  }

  return (
    <div className="space-y-8">
      {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">{error}</div>}
      {message && <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-sm">{message}</div>}

      {/* Create Backup */}
      <div className="glass-card p-8 space-y-6">
        <div className="flex items-center gap-3">
          <HardDrive className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-bold text-white tracking-tight">Create Backup</h2>
        </div>
        <p className="text-sm text-slate-400">Create a snapshot of your entire database and vector embeddings.</p>
        <div className="flex gap-3">
          <button
            onClick={() => handleCreateBackup("local")}
            disabled={creating}
            className="btn-primary py-2 px-6 text-sm"
          >
            {creating ? "Creating..." : "Backup to Local"}
          </button>
        </div>
      </div>

      {/* Backup List */}
      <div className="glass-card p-8 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Download className="w-5 h-5 text-secondary" />
            <h2 className="text-xl font-bold text-white tracking-tight">Available Backups</h2>
          </div>
          <button onClick={loadBackups} className="btn-secondary py-1.5 px-4 text-xs">
            <RefreshCw className="w-3 h-3 inline mr-1" /> Refresh
          </button>
        </div>

        {loading && <p className="text-sm text-slate-500 italic">Loading...</p>}
        {!loading && backups.length === 0 && (
          <p className="text-sm text-slate-500">No backups found.</p>
        )}
        {!loading && backups.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Filename</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Size</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Storage</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3 pr-4">Date</th>
                  <th className="text-[10px] font-black uppercase tracking-widest text-slate-500 pb-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((b) => (
                  <tr key={`${b.storage}-${b.filename}`} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="py-3 pr-4 text-slate-300 font-mono text-xs">{b.filename}</td>
                    <td className="py-3 pr-4 text-slate-400 text-xs">{formatBytes(b.size_bytes)}</td>
                    <td className="py-3 pr-4">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-slate-400 uppercase">
                        {b.storage === "s3" ? <Cloud className="w-3 h-3" /> : <HardDrive className="w-3 h-3" />}
                        {b.storage}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-400 text-xs">{new Date(b.created_at).toLocaleString()}</td>
                    <td className="py-3 flex gap-2">
                      {b.storage === "local" && (
                        <a
                          href={api.getBackupDownloadUrl(b.filename)}
                          className="text-primary hover:text-primary/80 text-xs font-bold"
                          download
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      )}
                      <button
                        onClick={() => handleRestore(undefined, b.storage === "local" ? b.filename : undefined)}
                        className="text-amber-400 hover:text-amber-300 text-xs font-bold"
                        title="Restore from this backup"
                      >
                        <Upload className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(b.storage === "s3" ? b.s3_key! : b.filename, b.storage)}
                        className="text-red-400 hover:text-red-300 text-xs font-bold"
                        title="Delete backup"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Restore from File */}
      <div className="glass-card p-8 space-y-6">
        <div className="flex items-center gap-3">
          <Upload className="w-5 h-5 text-amber-400" />
          <h2 className="text-xl font-bold text-white tracking-tight">Restore from File</h2>
        </div>
        <p className="text-sm text-slate-400">Upload a backup .zip file to restore your data. A safety backup will be created first.</p>
        <label className={`block w-full p-8 border-2 border-dashed rounded-2xl text-center cursor-pointer transition-colors ${restoring ? "border-slate-600 opacity-50" : "border-white/10 hover:border-primary/50"}`}>
          <input type="file" accept=".zip" onChange={handleFileUpload} disabled={restoring} className="hidden" />
          <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
          <p className="text-sm text-slate-400">{restoring ? "Restoring..." : "Drop a .zip backup file here or click to browse"}</p>
        </label>
      </div>
    </div>
  );
}
```

**Step 4: Add Data tab to Settings page**

In `packages/web-ui/src/pages/Settings.tsx`:

1. Add import: `import { DataTab } from "./settings/DataTab";`
2. Add import: `import { HardDrive } from "lucide-react";` (if not already)
3. Change Tab type: `type Tab = "general" | "data" | "messaging" | "system" | "scheduled-tasks";`
4. Add to tabs array: `{ key: "data", label: "Data" },`
5. Add rendering block:

```tsx
{activeTab === "data" && <DataTab />}
```

**Step 5: Verify build**

Run: `cd packages/web-ui && npm run build`
Expected: SUCCESS

**Step 6: Commit**

```bash
git add packages/web-ui/src/pages/settings/DataTab.tsx \
       packages/web-ui/src/pages/Settings.tsx \
       packages/web-ui/src/lib/api.ts \
       packages/web-ui/src/types/
git commit -m "feat: add Data tab in Settings for backup/restore management"
```

---

## Phase 7: Configuration & Environment

### Task 16: Update .env.example and documentation

**Files:**
- Modify: `.env.example`
- Modify: `CLAUDE.md` (storage layout section)
- Modify: `USECASES.md` (add backup use cases)

**Step 1: Update .env.example**

Add to `.env.example`:

```env
# --- Encryption (required for backup feature) ---
FLUX_SECRET_KEY=your-strong-secret-key-here

# --- Backup Settings ---
BACKUP_LOCAL_DIR=/data/backups
BACKUP_LOCAL_RETENTION=7
BACKUP_S3_RETENTION=30

# S3 credentials are stored encrypted in SQLite, configurable via Web UI Settings.
```

**Step 2: Update CLAUDE.md storage layout**

Add `/data/backups/` to the storage layout section.

**Step 3: Update USECASES.md**

Add backup use cases to the inventory.

**Step 4: Commit**

```bash
git add .env.example CLAUDE.md USECASES.md
git commit -m "docs: add backup/restore configuration and use case documentation"
```

---

## Phase 8: Retention Policy & Final Integration

### Task 17: Backup retention policy

**Files:**
- Modify: `packages/core/src/flux_core/use_cases/backup/create_backup.py`
- Test: add retention test to `packages/core/tests/test_use_cases/test_backup.py`

**Step 1: Write failing test**

Add to test file:

```python
async def test_create_backup_applies_retention(tmp_path):
    """After creating backup, old backups beyond retention limit are deleted."""
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)

    db = MagicMock()
    db._path = db_path
    db.connection.return_value = sqlite3.connect(db_path)

    local_provider = AsyncMock()
    local_provider.upload.return_value = "new-backup.zip"
    # Simulate 10 existing backups
    local_provider.list_backups.return_value = [
        _make_meta(f"backup-{i}.zip") for i in range(10)
    ]

    uc = CreateBackup(
        db=db, zvec_path=zvec_path, local_provider=local_provider,
        local_retention=3,
    )
    await uc.execute(storage="local")

    # Should have deleted backups beyond retention (10 - 3 = 7 deletions)
    assert local_provider.delete.call_count == 7
```

**Step 2: Add retention to CreateBackup**

Add `local_retention` and `s3_retention` params to `CreateBackup.__init__()`. After uploading, call `_apply_retention()`:

```python
    async def _apply_retention(self):
        if self._local and self._local_retention:
            backups = await self._local.list_backups()
            for old in backups[self._local_retention:]:
                await self._local.delete(old.filename)
        if self._s3 and self._s3_retention:
            backups = await self._s3.list_backups()
            for old in backups[self._s3_retention:]:
                await self._s3.delete(old.s3_key)
```

**Step 3: Run tests**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add packages/core/src/flux_core/use_cases/backup/create_backup.py \
       packages/core/tests/test_use_cases/test_backup.py
git commit -m "feat: add backup retention policy to CreateBackup"
```

---

### Task 18: Run full test suite and verify coverage

**Step 1: Run all tests**

Run: `./test-all.sh --coverage`
Expected: All tests pass, coverage >= 90% across all packages

**Step 2: Fix any failing tests or coverage gaps**

If coverage < 90%, add tests for uncovered paths.

**Step 3: Final commit**

```bash
git commit -m "test: ensure backup/restore feature meets 90% coverage threshold"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-7 | Core infrastructure: deps, migration, encryption, config repo, model, storage providers |
| 2 | 8-10 | Core use cases: CreateBackup, ListBackups, DeleteBackup, RestoreBackup |
| 3 | 11 | API server: REST endpoints |
| 4 | 12 | MCP server: tools registration |
| 5 | 13-14 | Agent bot: /backup, /restore commands, onboard backup preference |
| 6 | 15 | Web UI: Data tab in Settings |
| 7 | 16 | Configuration & documentation |
| 8 | 17-18 | Retention policy & coverage verification |

Total: **18 tasks**, estimated ~40 TDD cycles.
