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
