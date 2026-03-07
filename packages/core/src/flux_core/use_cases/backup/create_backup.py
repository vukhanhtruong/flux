"""CreateBackup use case — snapshot SQLite + zvec into a .zip archive."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import structlog

from flux_core.models.backup import BackupMetadata

if TYPE_CHECKING:
    from flux_core.services.storage.local import LocalStorageProvider
    from flux_core.services.storage.s3 import S3StorageProvider
    from flux_core.sqlite.database import Database

logger = structlog.get_logger(__name__)


class CreateBackup:
    def __init__(
        self,
        db: Database,
        zvec_path: str,
        local_provider: LocalStorageProvider | None = None,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._db = db
        self._zvec_path = zvec_path
        self._local = local_provider
        self._s3 = s3_provider

    async def execute(
        self,
        storage: Literal["local", "s3", "both"] = "local",
    ) -> BackupMetadata:
        self._resolve_provider(storage)

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S")
        filename = f"flux-backup-{timestamp}.zip"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            zip_path = tmp / filename

            # 1. SQLite backup via connection.backup()
            db_backup = tmp / "flux.db"
            src_conn = self._db.connection()
            dst_conn = sqlite3.connect(str(db_backup))
            src_conn.backup(dst_conn)
            dst_conn.close()

            # 2. Copy zvec directory
            zvec_src = Path(self._zvec_path)
            zvec_dst = tmp / "zvec"
            if zvec_src.exists():
                shutil.copytree(zvec_src, zvec_dst)

            # 3. Create zip
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_backup, "flux.db")
                if zvec_dst.exists():
                    for f in zvec_dst.rglob("*"):
                        if f.is_file():
                            arcname = f"zvec/{f.relative_to(zvec_dst)}"
                            zf.write(f, arcname)

            # 4. Upload to storage(s)
            result_meta = None
            if storage in ("local", "both") and self._local:
                key = await self._local.upload(zip_path, filename)
                result_meta = BackupMetadata(
                    id=timestamp,
                    filename=filename,
                    size_bytes=zip_path.stat().st_size,
                    created_at=datetime.now(UTC),
                    storage="local",
                    local_path=key,
                )
            if storage in ("s3", "both") and self._s3:
                key = await self._s3.upload(zip_path, filename)
                result_meta = BackupMetadata(
                    id=timestamp,
                    filename=filename,
                    size_bytes=zip_path.stat().st_size,
                    created_at=datetime.now(UTC),
                    storage="s3",
                    s3_key=key,
                )

        return result_meta

    def _resolve_provider(self, storage: str) -> None:
        if storage == "local" and not self._local:
            raise ValueError("No storage provider available for 'local'")
        if storage == "s3" and not self._s3:
            raise ValueError("No storage provider available for 's3'")
        if storage == "both" and not (self._local or self._s3):
            raise ValueError("No storage provider available")
