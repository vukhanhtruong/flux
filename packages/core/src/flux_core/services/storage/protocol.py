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
