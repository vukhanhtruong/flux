"""Local filesystem backup storage provider."""
from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from flux_core.models.backup import BackupMetadata


class LocalStorageProvider:
    def __init__(self, backup_dir: str):
        self._dir = Path(backup_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_path: Path, key: str) -> str:
        dest = self._dir / key
        shutil.copy2(file_path, dest)
        return key

    async def download(self, key: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        src = self._dir / key
        target = dest / key
        shutil.copy2(src, target)
        return target

    async def list_backups(self) -> list[BackupMetadata]:
        if not self._dir.exists():
            return []
        backups = []
        for f in sorted(self._dir.glob("*.zip"), reverse=True):
            stat = f.stat()
            backups.append(
                BackupMetadata(
                    id=str(uuid4()),
                    filename=f.name,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    storage="local",
                    local_path=str(f),
                )
            )
        return backups

    async def delete(self, key: str) -> None:
        path = self._dir / key
        if path.exists():
            path.unlink()
