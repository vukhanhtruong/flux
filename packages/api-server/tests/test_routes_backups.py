"""Test backup REST routes."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_core.models.backup import BackupMetadata


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


def _make_backup(**overrides) -> BackupMetadata:
    defaults = dict(
        id="2026-03-07T120000",
        filename="flux-backup-2026-03-07T120000.zip",
        size_bytes=1024,
        created_at=datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC),
        storage="local",
        local_path="/data/backups/flux-backup-2026-03-07T120000.zip",
    )
    defaults.update(overrides)
    return BackupMetadata(**defaults)


def test_create_backup(client):
    """Test POST /backups/ creates a backup and returns 201."""
    expected = _make_backup()

    with (
        patch("flux_api.routes.backups.get_db") as mock_get_db,
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
        patch("flux_api.routes.backups.CreateBackup") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        mock_get_local.return_value = MagicMock()
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=expected)
        MockUC.return_value = mock_uc

        response = client.post("/backups/", params={"storage": "local"})

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "flux-backup-2026-03-07T120000.zip"
    assert data["storage"] == "local"
    assert data["size_bytes"] == 1024


def test_create_backup_default_storage(client):
    """Test POST /backups/ defaults to local storage."""
    expected = _make_backup()

    with (
        patch("flux_api.routes.backups.get_db") as mock_get_db,
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
        patch("flux_api.routes.backups.CreateBackup") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        mock_get_local.return_value = MagicMock()
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=expected)
        MockUC.return_value = mock_uc

        response = client.post("/backups/")

    assert response.status_code == 201
    MockUC.return_value.execute.assert_called_once_with(storage="local")


def test_list_backups(client):
    """Test GET /backups/ returns list of backups."""
    backups = [
        _make_backup(),
        _make_backup(
            id="2026-03-06T100000",
            filename="flux-backup-2026-03-06T100000.zip",
            created_at=datetime(2026, 3, 6, 10, 0, 0, tzinfo=UTC),
        ),
    ]

    with (
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
        patch("flux_api.routes.backups.ListBackups") as MockUC,
    ):
        mock_get_local.return_value = MagicMock()
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=backups)
        MockUC.return_value = mock_uc

        response = client.get("/backups/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["filename"] == "flux-backup-2026-03-07T120000.zip"


def test_delete_backup(client):
    """Test DELETE /backups/{key} returns 204."""
    with (
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
        patch("flux_api.routes.backups.DeleteBackup") as MockUC,
    ):
        mock_get_local.return_value = MagicMock()
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=None)
        MockUC.return_value = mock_uc

        response = client.delete(
            "/backups/flux-backup-2026-03-07T120000.zip",
            params={"storage": "local"},
        )

    assert response.status_code == 204


def test_delete_backup_default_storage(client):
    """Test DELETE /backups/{key} defaults to local storage."""
    with (
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
        patch("flux_api.routes.backups.DeleteBackup") as MockUC,
    ):
        mock_get_local.return_value = MagicMock()
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=None)
        MockUC.return_value = mock_uc

        response = client.delete("/backups/flux-backup-2026-03-07T120000.zip")

    assert response.status_code == 204
    MockUC.return_value.execute.assert_called_once_with(
        "flux-backup-2026-03-07T120000.zip", storage="local"
    )


def test_restore_backup_with_backup_id(client):
    """Test POST /backups/restore with backup_id query param."""
    with (
        patch("flux_api.routes.backups.get_db") as mock_get_db,
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
        patch("flux_api.routes.backups.RestoreBackup") as MockUC,
    ):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_local = MagicMock()
        mock_local.download = AsyncMock(return_value="/tmp/backup.zip")
        mock_get_local.return_value = mock_local
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=None)
        MockUC.return_value = mock_uc

        response = client.post(
            "/backups/restore",
            params={"backup_id": "flux-backup-2026-03-07T120000.zip"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "restored"


def test_restore_backup_no_source(client):
    """Test POST /backups/restore without file or backup_id returns 400."""
    with (
        patch("flux_api.routes.backups.get_db") as mock_get_db,
        patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        patch("flux_api.routes.backups.get_s3_storage", return_value=None),
    ):
        mock_get_db.return_value = MagicMock()
        mock_get_local.return_value = MagicMock()

        response = client.post("/backups/restore")

    assert response.status_code == 400


def test_download_backup(client):
    """Test GET /backups/{filename}/download returns file."""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(b"fake zip content")
        tmp_path = f.name

    try:
        with (
            patch("flux_api.routes.backups.get_local_storage") as mock_get_local,
        ):
            mock_local = MagicMock()
            mock_local._dir = Path(tmp_path).parent
            # Make download return the temp file path
            mock_get_local.return_value = mock_local

            # Patch Path resolution to return our temp file
            with patch(
                "flux_api.routes.backups.Path"
            ) as MockPath:
                mock_path = MagicMock()
                mock_path.__truediv__ = MagicMock(return_value=Path(tmp_path))
                mock_path.exists.return_value = True
                MockPath.return_value = mock_path
                # The route uses local._dir / filename, so mock _dir
                mock_local._dir = MagicMock()
                mock_local._dir.__truediv__ = MagicMock(return_value=Path(tmp_path))
                result_path = mock_local._dir / "test.zip"
                assert result_path == Path(tmp_path)

                response = client.get("/backups/test.zip/download")

        assert response.status_code == 200
        assert response.content == b"fake zip content"
    finally:
        import os
        os.unlink(tmp_path)


def test_get_backup_config(client):
    """Test GET /backups/config returns S3 configuration."""
    mock_repo = MagicMock()
    mock_repo.get_by_prefix.return_value = {
        "s3_endpoint": "https://r2.example.com",
        "s3_bucket": "my-bucket",
        "s3_region": "auto",
        "s3_access_key": "AKID",
        "s3_secret_key": "secret123",
    }

    with patch("flux_api.routes.backups.get_system_config_repo", return_value=mock_repo):
        response = client.get("/backups/config")

    assert response.status_code == 200
    data = response.json()
    assert data["s3_endpoint"] == "https://r2.example.com"
    assert data["s3_bucket"] == "my-bucket"
    assert data["s3_access_key"] == "AKID"
    mock_repo.get_by_prefix.assert_called_once_with("s3_")


def test_get_backup_config_no_secret_key(client):
    """Test GET /backups/config returns empty config when FLUX_SECRET_KEY is not set."""
    with patch("flux_api.routes.backups.get_system_config_repo", return_value=None):
        response = client.get("/backups/config")

    assert response.status_code == 200
    data = response.json()
    assert data["s3_endpoint"] == ""
    assert data["s3_bucket"] == ""


def test_update_backup_config(client):
    """Test PUT /backups/config saves S3 configuration with encryption for sensitive keys."""
    mock_repo = MagicMock()

    with patch("flux_api.routes.backups.get_system_config_repo", return_value=mock_repo):
        response = client.put(
            "/backups/config",
            json={
                "s3_endpoint": "https://r2.example.com",
                "s3_bucket": "my-bucket",
                "s3_region": "auto",
                "s3_access_key": "AKID",
                "s3_secret_key": "secret123",
            },
        )

    assert response.status_code == 200
    # Non-sensitive keys stored without encryption
    mock_repo.set.assert_any_call("s3_endpoint", "https://r2.example.com", encrypted=False)
    mock_repo.set.assert_any_call("s3_bucket", "my-bucket", encrypted=False)
    mock_repo.set.assert_any_call("s3_region", "auto", encrypted=False)
    # Sensitive keys stored with encryption
    mock_repo.set.assert_any_call("s3_access_key", "AKID", encrypted=True)
    mock_repo.set.assert_any_call("s3_secret_key", "secret123", encrypted=True)


def test_update_backup_config_no_secret_key(client):
    """Test PUT /backups/config returns 400 when FLUX_SECRET_KEY is not set."""
    with patch("flux_api.routes.backups.get_system_config_repo", return_value=None):
        response = client.put(
            "/backups/config",
            json={
                "s3_endpoint": "https://r2.example.com",
                "s3_bucket": "my-bucket",
                "s3_region": "",
                "s3_access_key": "AKID",
                "s3_secret_key": "secret123",
            },
        )

    assert response.status_code == 400
    assert "FLUX_SECRET_KEY" in response.json()["detail"]


def test_update_backup_config_deletes_empty_values(client):
    """Test PUT /backups/config deletes keys with empty values."""
    mock_repo = MagicMock()

    with patch("flux_api.routes.backups.get_system_config_repo", return_value=mock_repo):
        response = client.put(
            "/backups/config",
            json={
                "s3_endpoint": "https://r2.example.com",
                "s3_bucket": "",
                "s3_region": "",
                "s3_access_key": "",
                "s3_secret_key": "",
            },
        )

    assert response.status_code == 200
    mock_repo.set.assert_called_once_with("s3_endpoint", "https://r2.example.com", encrypted=False)
    assert mock_repo.delete.call_count == 4
