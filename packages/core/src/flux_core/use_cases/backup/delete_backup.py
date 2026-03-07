"""DeleteBackup use case — delete a backup from specified storage."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from flux_core.services.storage.local import LocalStorageProvider
    from flux_core.services.storage.s3 import S3StorageProvider


class DeleteBackup:
    def __init__(
        self,
        local_provider: LocalStorageProvider | None = None,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._local = local_provider
        self._s3 = s3_provider

    async def execute(
        self, key: str, *, storage: Literal["local", "s3"] = "local"
    ) -> None:
        if storage == "local" and self._local:
            await self._local.delete(key)
        elif storage == "s3" and self._s3:
            await self._s3.delete(key)
