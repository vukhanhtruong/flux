"""Tests for S3StorageProvider (mocked boto3)."""
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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
