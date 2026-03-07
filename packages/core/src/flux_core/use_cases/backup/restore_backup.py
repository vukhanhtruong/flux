"""RestoreBackup use case — auto-backup then replace SQLite + zvec."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from flux_core.services.storage.s3 import S3StorageProvider
    from flux_core.sqlite.database import Database
    from flux_core.use_cases.backup.create_backup import CreateBackup

logger = structlog.get_logger(__name__)


class RestoreBackup:
    def __init__(
        self,
        db: Database,
        zvec_path: str,
        create_backup: CreateBackup,
        s3_provider: S3StorageProvider | None = None,
    ):
        self._db = db
        self._zvec_path = zvec_path
        self._create_backup = create_backup
        self._s3 = s3_provider

    async def execute(
        self,
        *,
        file_path: Path | None = None,
        s3_key: str | None = None,
    ) -> None:
        if not file_path and not s3_key:
            raise ValueError("Provide either file_path or s3_key")

        # 1. Auto-backup current data
        logger.info("Creating safety backup before restore")
        await self._create_backup.execute(storage="local")

        # 2. Get the backup zip
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            if s3_key and self._s3:
                zip_path = await self._s3.download(s3_key, tmp)
            elif file_path:
                zip_path = file_path
            else:
                raise ValueError("S3 provider not configured")

            # 3. Validate zip contents
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                if "flux.db" not in names:
                    raise ValueError("Invalid backup: missing flux.db")

            # 4. Extract to temp
            extract_dir = tmp / "extracted"
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)

            # 5. Validate SQLite integrity
            restored_db = extract_dir / "flux.db"
            test_conn = sqlite3.connect(str(restored_db))
            result = test_conn.execute("PRAGMA integrity_check").fetchone()
            test_conn.close()
            if result[0] != "ok":
                raise ValueError(
                    f"Backup database integrity check failed: {result[0]}"
                )

            # 6. Disconnect, replace, reconnect
            self._db.disconnect()

            db_path = Path(self._db._path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(restored_db, db_path)
            for suffix in ("-wal", "-shm"):
                wal = db_path.with_name(db_path.name + suffix)
                if wal.exists():
                    wal.unlink()

            restored_zvec = extract_dir / "zvec"
            if restored_zvec.exists():
                zvec_dest = Path(self._zvec_path)
                if zvec_dest.exists():
                    shutil.rmtree(zvec_dest)
                shutil.copytree(restored_zvec, zvec_dest)

            # 7. Reconnect
            self._db.connect()
            logger.info("Restore completed successfully")
