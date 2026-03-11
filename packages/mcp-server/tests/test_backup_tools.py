"""Unit tests for backup MCP tools."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import FastMCP
from flux_core.models.backup import BackupMetadata


async def test_restore_backup_tool_not_registered():
    """restore_backup should NOT be registered as an MCP tool (admin-only via CLI)."""
    mcp = FastMCP("test")
    from flux_mcp.tools.backup_tools import register_backup_tools

    register_backup_tools(
        mcp=mcp,
        get_db=MagicMock,
        get_local_storage=MagicMock,
        get_s3_storage=MagicMock,
    )
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "restore_backup" not in tool_names
    # Verify other backup tools are still registered
    assert "create_backup" in tool_names
    assert "list_backups" in tool_names
    assert "delete_backup" in tool_names


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


async def test_create_backup_auto_prefers_s3():
    """create_backup with storage='auto' uses S3 when available."""
    meta = BackupMetadata(
        id="2026-03-11T120000",
        filename="flux-backup-2026-03-11T120000.zip",
        size_bytes=2048,
        created_at=datetime(2026, 3, 11, 12, 0, 0, tzinfo=UTC),
        storage="s3",
        s3_key="backups/flux-backup-2026-03-11T120000.zip",
    )

    mock_db = MagicMock()
    mock_local_storage = MagicMock()
    mock_s3_storage = MagicMock()

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
            storage="auto",
        )

    assert result["status"] == "ok"
    assert result["storage"] == "s3"
    mock_uc.execute.assert_awaited_once_with(storage="s3")


async def test_create_backup_auto_falls_back_to_local():
    """create_backup with storage='auto' falls back to local when S3 unavailable."""
    meta = BackupMetadata(
        id="2026-03-11T120000",
        filename="flux-backup-2026-03-11T120000.zip",
        size_bytes=1024,
        created_at=datetime(2026, 3, 11, 12, 0, 0, tzinfo=UTC),
        storage="local",
        local_path="/data/backups/flux-backup-2026-03-11T120000.zip",
    )

    mock_db = MagicMock()
    mock_local_storage = MagicMock()

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
            s3_storage=None,
            storage="auto",
        )

    assert result["status"] == "ok"
    assert result["storage"] == "local"
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


async def test_delete_backup_tool():
    """delete_backup tool instantiates DeleteBackup use case and returns ok."""
    mock_local_storage = MagicMock()
    mock_s3_storage = None

    with patch(
        "flux_mcp.tools.backup_tools.DeleteBackup"
    ) as MockDeleteBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = None
        MockDeleteBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _delete_backup_impl

        result = await _delete_backup_impl(
            local_storage=mock_local_storage,
            s3_storage=mock_s3_storage,
            key="flux-backup-2026-03-07T120000.zip",
            storage="local",
        )

    assert result["status"] == "ok"
    assert result["key"] == "flux-backup-2026-03-07T120000.zip"
    assert result["storage"] == "local"
    MockDeleteBackup.assert_called_once_with(mock_local_storage, mock_s3_storage)
    mock_uc.execute.assert_awaited_once_with(
        "flux-backup-2026-03-07T120000.zip", storage="local"
    )


async def test_delete_backup_tool_s3():
    """delete_backup tool works with S3 storage."""
    mock_local_storage = None
    mock_s3_storage = MagicMock()

    with patch(
        "flux_mcp.tools.backup_tools.DeleteBackup"
    ) as MockDeleteBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = None
        MockDeleteBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _delete_backup_impl

        result = await _delete_backup_impl(
            local_storage=mock_local_storage,
            s3_storage=mock_s3_storage,
            key="flux-backup-2026-03-07T120000.zip",
            storage="s3",
        )

    assert result["status"] == "ok"
    assert result["storage"] == "s3"
    mock_uc.execute.assert_awaited_once_with(
        "flux-backup-2026-03-07T120000.zip", storage="s3"
    )


async def test_delete_backup_tool_error():
    """delete_backup tool returns error dict on failure."""
    with patch(
        "flux_mcp.tools.backup_tools.DeleteBackup"
    ) as MockDeleteBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.side_effect = OSError("File not found")
        MockDeleteBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _delete_backup_impl

        result = await _delete_backup_impl(
            local_storage=None,
            s3_storage=None,
            key="nonexistent.zip",
            storage="local",
        )

    assert result["status"] == "error"
    assert "File not found" in result["error"]


async def test_restore_backup_tool_local():
    """restore_backup tool restores from local file path."""
    mock_db = MagicMock()
    mock_local_storage = MagicMock()
    mock_s3_storage = None

    with patch(
        "flux_mcp.tools.backup_tools.RestoreBackup"
    ) as MockRestoreBackup, patch(
        "flux_mcp.tools.backup_tools.CreateBackup"
    ) as MockCreateBackup:
        mock_create_uc = MagicMock()
        MockCreateBackup.return_value = mock_create_uc

        mock_uc = AsyncMock()
        mock_uc.execute.return_value = None
        MockRestoreBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _restore_backup_impl

        result = await _restore_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=mock_local_storage,
            s3_storage=mock_s3_storage,
            file_path="/data/backups/flux-backup-2026-03-07T120000.zip",
            s3_key=None,
        )

    assert result["status"] == "ok"
    assert result["source"] == "local"
    MockCreateBackup.assert_called_once_with(
        mock_db, "/data/zvec", mock_local_storage, mock_s3_storage
    )
    MockRestoreBackup.assert_called_once_with(
        mock_db, "/data/zvec", mock_create_uc, mock_s3_storage
    )
    from pathlib import Path

    mock_uc.execute.assert_awaited_once_with(
        file_path=Path("/data/backups/flux-backup-2026-03-07T120000.zip"),
        s3_key=None,
    )


async def test_restore_backup_tool_s3():
    """restore_backup tool restores from S3 key."""
    mock_db = MagicMock()
    mock_s3_storage = MagicMock()

    with patch(
        "flux_mcp.tools.backup_tools.RestoreBackup"
    ) as MockRestoreBackup, patch(
        "flux_mcp.tools.backup_tools.CreateBackup"
    ) as MockCreateBackup:
        mock_create_uc = MagicMock()
        MockCreateBackup.return_value = mock_create_uc

        mock_uc = AsyncMock()
        mock_uc.execute.return_value = None
        MockRestoreBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _restore_backup_impl

        result = await _restore_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=None,
            s3_storage=mock_s3_storage,
            file_path=None,
            s3_key="backups/flux-backup-2026-03-07T120000.zip",
        )

    assert result["status"] == "ok"
    assert result["source"] == "s3"
    mock_uc.execute.assert_awaited_once_with(
        file_path=None,
        s3_key="backups/flux-backup-2026-03-07T120000.zip",
    )


async def test_restore_backup_tool_error():
    """restore_backup tool returns error dict on failure."""
    mock_db = MagicMock()

    with patch(
        "flux_mcp.tools.backup_tools.RestoreBackup"
    ) as MockRestoreBackup, patch(
        "flux_mcp.tools.backup_tools.CreateBackup"
    ):
        mock_uc = AsyncMock()
        mock_uc.execute.side_effect = ValueError("Provide either file_path or s3_key")
        MockRestoreBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _restore_backup_impl

        result = await _restore_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=None,
            s3_storage=None,
            file_path=None,
            s3_key=None,
        )

    assert result["status"] == "error"
    assert "Provide either file_path or s3_key" in result["error"]
