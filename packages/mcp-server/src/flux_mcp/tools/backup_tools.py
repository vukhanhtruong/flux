"""MCP tools for backup and restore operations."""
from __future__ import annotations

import os
from typing import Callable

from fastmcp import FastMCP
from flux_core.sqlite.database import Database
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.list_backups import ListBackups


async def _create_backup_impl(
    db: Database,
    zvec_path: str,
    local_storage,
    s3_storage,
    storage: str = "local",
) -> dict:
    """Internal implementation for create_backup tool."""
    try:
        uc = CreateBackup(db, zvec_path, local_storage, s3_storage)
        meta = await uc.execute(storage=storage)
        return {
            "status": "ok",
            "filename": meta.filename,
            "size_bytes": meta.size_bytes,
            "storage": meta.storage,
            "created_at": str(meta.created_at),
        }
    except (ValueError, OSError) as exc:
        return {"status": "error", "error": str(exc)}


async def _list_backups_impl(local_storage, s3_storage) -> list[dict]:
    """Internal implementation for list_backups tool."""
    uc = ListBackups(local_storage, s3_storage)
    backups = await uc.execute()
    return [
        {
            "filename": b.filename,
            "size_bytes": b.size_bytes,
            "storage": b.storage,
            "created_at": str(b.created_at),
        }
        for b in backups
    ]


def register_backup_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_local_storage: Callable,
    get_s3_storage: Callable,
):
    @mcp.tool()
    async def create_backup(storage: str = "local") -> dict:
        """Create a backup of the database and vector store.

        Args:
            storage: Where to store the backup — "local", "s3", or "both".
        """
        zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
        return await _create_backup_impl(
            db=get_db(),
            zvec_path=zvec_path,
            local_storage=get_local_storage(),
            s3_storage=get_s3_storage(),
            storage=storage,
        )

    @mcp.tool()
    async def list_backups() -> list[dict]:
        """List all available backups from local and S3 storage."""
        return await _list_backups_impl(
            local_storage=get_local_storage(),
            s3_storage=get_s3_storage(),
        )
