"""Unit tests for backup MCP tools."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from flux_core.models.backup import BackupMetadata


async def test_create_backup_tool():
    """create_backup tool instantiates CreateBackup use case and returns dict."""
    meta = BackupMetadata(
        id="2026-03-07T120000",
        filename="flux-backup-2026-03-07T120000.zip",
        size_bytes=1024,
        created_at=datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC),
        storage="local",
        local_path="/data/backups/flux-backup-2026-03-07T120000.zip",
    )

    mock_db = MagicMock()
    mock_local_storage = MagicMock()
    mock_s3_storage = None

    with patch(
        "flux_mcp.tools.backup_tools.CreateBackup"
    ) as MockCreateBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = meta
        MockCreateBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _create_backup_impl

        result = await _create_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=mock_local_storage,
            s3_storage=mock_s3_storage,
            storage="local",
        )

    assert result["status"] == "ok"
    assert result["filename"] == "flux-backup-2026-03-07T120000.zip"
    assert result["size_bytes"] == 1024
    assert result["storage"] == "local"
    MockCreateBackup.assert_called_once_with(
        mock_db, "/data/zvec", mock_local_storage, mock_s3_storage,
    )
    mock_uc.execute.assert_awaited_once_with(storage="local")


async def test_create_backup_tool_error():
    """create_backup tool returns error dict on failure."""
    mock_db = MagicMock()

    with patch(
        "flux_mcp.tools.backup_tools.CreateBackup"
    ) as MockCreateBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.side_effect = ValueError("No storage provider available for 's3'")
        MockCreateBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _create_backup_impl

        result = await _create_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=None,
            s3_storage=None,
            storage="s3",
        )

    assert result["status"] == "error"
    assert "No storage provider" in result["error"]


async def test_list_backups_tool():
    """list_backups tool returns list of backup dicts."""
    backups = [
        BackupMetadata(
            id="2026-03-07T120000",
            filename="flux-backup-2026-03-07T120000.zip",
            size_bytes=1024,
            created_at=datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC),
            storage="local",
            local_path="/data/backups/flux-backup-2026-03-07T120000.zip",
        ),
        BackupMetadata(
            id="2026-03-06T100000",
            filename="flux-backup-2026-03-06T100000.zip",
            size_bytes=2048,
            created_at=datetime(2026, 3, 6, 10, 0, 0, tzinfo=UTC),
            storage="local",
            local_path="/data/backups/flux-backup-2026-03-06T100000.zip",
        ),
    ]

    with patch(
        "flux_mcp.tools.backup_tools.ListBackups"
    ) as MockListBackups:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = backups
        MockListBackups.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _list_backups_impl

        result = await _list_backups_impl(
            local_storage=MagicMock(),
            s3_storage=None,
        )

    assert len(result) == 2
    assert result[0]["filename"] == "flux-backup-2026-03-07T120000.zip"
    assert result[0]["size_bytes"] == 1024
    assert result[0]["storage"] == "local"
    assert result[1]["filename"] == "flux-backup-2026-03-06T100000.zip"


async def test_list_backups_tool_empty():
    """list_backups tool returns empty list when no backups exist."""
    with patch(
        "flux_mcp.tools.backup_tools.ListBackups"
    ) as MockListBackups:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = []
        MockListBackups.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _list_backups_impl

        result = await _list_backups_impl(
            local_storage=None,
            s3_storage=None,
        )

    assert result == []
