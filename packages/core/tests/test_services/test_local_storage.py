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
