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
