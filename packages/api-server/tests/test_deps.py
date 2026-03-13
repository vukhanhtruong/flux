"""Test FastAPI dependency providers."""
from unittest.mock import MagicMock, patch

import pytest

import flux_core.infrastructure as infra
import flux_api.deps as deps


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all module-level singletons before each test."""
    infra.reset_singletons()
    yield
    infra.reset_singletons()


def test_get_db_lazy_init(tmp_path):
    """Test get_db() creates Database, connects, and migrates on first call."""
    db_path = str(tmp_path / "test.db")
    with patch.dict("os.environ", {"DATABASE_PATH": db_path}):
        db = deps.get_db()

    assert db is not None
    assert infra._db is db
    # Second call returns same instance
    assert deps.get_db() is db


def test_get_vector_store_lazy_init(tmp_path):
    """Test get_vector_store() creates ZvecStore on first call."""
    zvec_path = str(tmp_path / "zvec")
    with patch.dict("os.environ", {"ZVEC_PATH": zvec_path}):
        store = deps.get_vector_store()

    assert store is not None
    assert infra._vector_store is store
    # Second call returns same instance
    assert deps.get_vector_store() is store


def test_get_event_bus_lazy_init():
    """Test get_event_bus() creates EventBus on first call."""
    bus = deps.get_event_bus()

    assert bus is not None
    assert infra._event_bus is bus
    assert deps.get_event_bus() is bus


def test_get_local_storage_lazy_init(tmp_path):
    """Test get_local_storage() creates LocalStorageProvider on first call."""
    backup_dir = str(tmp_path / "backups")
    with patch.dict("os.environ", {"BACKUP_LOCAL_DIR": backup_dir}):
        storage = deps.get_local_storage()

    assert storage is not None
    assert infra._local_storage is storage
    assert deps.get_local_storage() is storage


def test_get_embedding_service_lazy_init():
    """Test get_embedding_service() creates EmbeddingService on first call."""
    mock_svc = MagicMock()
    with patch("flux_core.infrastructure.EmbeddingService", return_value=mock_svc):
        svc = deps.get_embedding_service()

    assert svc is mock_svc
    assert infra._embedding_service is svc
    assert deps.get_embedding_service() is svc


def test_get_s3_storage_returns_none_without_secret_key():
    """Test get_s3_storage() returns None when FLUX_SECRET_KEY is not set."""
    # EncryptionService.from_env() raises ValueError without FLUX_SECRET_KEY
    with patch.dict("os.environ", {}, clear=False):
        result = deps.get_s3_storage()

    assert result is None


def test_get_s3_storage_returns_none_when_config_incomplete():
    """Test get_s3_storage() returns None when S3 config is incomplete."""
    mock_enc = MagicMock()
    mock_config_repo = MagicMock()
    mock_config_repo.get.return_value = None  # All config keys return None

    mock_db = MagicMock()
    infra._db = mock_db

    with (
        patch("flux_core.services.encryption.EncryptionService") as MockEnc,
        patch(
            "flux_core.sqlite.system_config_repo.SqliteSystemConfigRepository",
            return_value=mock_config_repo,
        ),
    ):
        MockEnc.from_env.return_value = mock_enc
        result = deps.get_s3_storage()

    assert result is None


def test_get_s3_storage_returns_provider_when_configured():
    """Test get_s3_storage() returns S3StorageProvider when fully configured."""
    mock_enc = MagicMock()
    mock_config_repo = MagicMock()
    mock_config_repo.get.side_effect = lambda key: {
        "s3_endpoint": "https://s3.example.com",
        "s3_bucket": "my-bucket",
        "s3_access_key": "AKID",
        "s3_secret_key": "secret",
        "s3_region": "us-east-1",
    }.get(key)

    mock_db = MagicMock()
    infra._db = mock_db

    mock_s3_provider = MagicMock()
    with (
        patch("flux_core.services.encryption.EncryptionService") as MockEnc,
        patch(
            "flux_core.sqlite.system_config_repo.SqliteSystemConfigRepository",
            return_value=mock_config_repo,
        ),
        patch(
            "flux_core.services.storage.s3.S3StorageProvider",
            return_value=mock_s3_provider,
        ),
    ):
        MockEnc.from_env.return_value = mock_enc
        result = deps.get_s3_storage()

    assert result is not None


def test_get_system_config_repo_returns_none_without_secret_key():
    """Test get_system_config_repo() returns None when FLUX_SECRET_KEY is not set."""
    result = deps.get_system_config_repo()
    assert result is None


def test_get_system_config_repo_returns_repo_when_configured():
    """Test get_system_config_repo() returns repo when FLUX_SECRET_KEY is set."""
    mock_enc = MagicMock()
    mock_repo = MagicMock()
    mock_db = MagicMock()
    infra._db = mock_db

    with (
        patch("flux_core.services.encryption.EncryptionService") as MockEnc,
        patch(
            "flux_core.sqlite.system_config_repo.SqliteSystemConfigRepository",
            return_value=mock_repo,
        ),
    ):
        MockEnc.from_env.return_value = mock_enc
        result = deps.get_system_config_repo()

    assert result is mock_repo


def test_get_uow_creates_unit_of_work():
    """Test get_uow() creates a UnitOfWork with db, vector_store, and event_bus."""
    mock_db = MagicMock()
    mock_vs = MagicMock()
    mock_bus = MagicMock()
    infra._db = mock_db
    infra._vector_store = mock_vs
    infra._event_bus = mock_bus

    with patch("flux_core.infrastructure.UnitOfWork") as MockUoW:
        deps.get_uow()

    MockUoW.assert_called_once_with(mock_db, mock_vs, mock_bus)
