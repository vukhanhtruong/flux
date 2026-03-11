"""Backup/restore REST routes — thin adapters over use cases."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from flux_api.deps import get_db, get_local_storage, get_s3_storage, get_system_config_repo
from flux_core.models.backup import BackupMetadata
from flux_core.use_cases.backup.create_backup import CreateBackup
from flux_core.use_cases.backup.delete_backup import DeleteBackup
from flux_core.use_cases.backup.list_backups import ListBackups
from flux_core.use_cases.backup.restore_backup import RestoreBackup

router = APIRouter(prefix="/backups", tags=["backups"])

S3_CONFIG_KEYS = ["s3_endpoint", "s3_bucket", "s3_region", "s3_access_key", "s3_secret_key"]
S3_SENSITIVE_KEYS = {"s3_access_key", "s3_secret_key"}


class S3Config(BaseModel):
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_backup(
    storage: Literal["local", "s3", "both"] = "local",
) -> BackupMetadata:
    """Create a new backup."""
    db = get_db()
    zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
    uc = CreateBackup(
        db,
        zvec_path,
        local_provider=get_local_storage(),
        s3_provider=get_s3_storage(),
    )
    return await uc.execute(storage=storage)


@router.get("/")
async def list_backups() -> list[BackupMetadata]:
    """List all backups."""
    uc = ListBackups(
        local_provider=get_local_storage(),
        s3_provider=get_s3_storage(),
    )
    return await uc.execute()


@router.get("/{filename}/download")
async def download_backup(
    filename: str,
    storage: Literal["local", "s3"] = "local",
    s3_key: str | None = None,
):
    """Download a backup file from local or S3 storage."""
    if storage == "s3":
        s3 = get_s3_storage()
        if s3 is None:
            raise HTTPException(status_code=400, detail="S3 storage is not configured")
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            downloaded = await s3.download(s3_key or f"backups/{filename}", tmp_dir)
            return FileResponse(
                path=str(downloaded),
                filename=filename,
                media_type="application/zip",
                background=BackgroundTask(lambda: shutil.rmtree(tmp_dir, ignore_errors=True)),
            )
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(status_code=404, detail="Backup file not found in S3")

    local = get_local_storage()
    file_path = local._dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/zip",
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile | None = File(None),
    backup_id: str | None = None,
    storage: Literal["local", "s3"] = "local",
) -> dict:
    """Restore from a backup file upload, or from a backup_id in local/S3 storage."""
    db = get_db()
    zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
    local = get_local_storage()
    s3 = get_s3_storage()

    create_uc = CreateBackup(db, zvec_path, local_provider=local, s3_provider=s3)
    uc = RestoreBackup(db, zvec_path, create_backup=create_uc, s3_provider=s3)

    if file and file.filename:
        # Multipart file upload
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        try:
            await uc.execute(file_path=tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        return {"status": "restored", "source": "upload"}

    elif backup_id:
        with tempfile.TemporaryDirectory() as tmpdir:
            if storage == "s3" and s3:
                downloaded = await s3.download(backup_id, Path(tmpdir))
            else:
                downloaded = await local.download(backup_id, Path(tmpdir))
            await uc.execute(file_path=Path(downloaded))
        return {"status": "restored", "source": storage, "backup_id": backup_id}

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either a file upload or backup_id query parameter",
        )


@router.delete("/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    key: str,
    storage: Literal["local", "s3"] = "local",
) -> None:
    """Delete a backup."""
    uc = DeleteBackup(
        local_provider=get_local_storage(),
        s3_provider=get_s3_storage(),
    )
    await uc.execute(key, storage=storage)


@router.get("/config")
async def get_backup_config() -> S3Config:
    """Get S3 backup configuration."""
    repo = get_system_config_repo()
    if repo is None:
        return S3Config()
    config = repo.get_by_prefix("s3_")
    return S3Config(
        s3_endpoint=config.get("s3_endpoint", ""),
        s3_bucket=config.get("s3_bucket", ""),
        s3_region=config.get("s3_region", ""),
        s3_access_key=config.get("s3_access_key", ""),
        s3_secret_key=config.get("s3_secret_key", ""),
    )


@router.put("/config")
async def update_backup_config(config: S3Config) -> S3Config:
    """Update S3 backup configuration."""
    repo = get_system_config_repo()
    if repo is None:
        raise HTTPException(
            status_code=400,
            detail="FLUX_SECRET_KEY not set. Cannot store encrypted config.",
        )
    data = config.model_dump()
    for key in S3_CONFIG_KEYS:
        value = data.get(key, "")
        if value:
            repo.set(key, value, encrypted=key in S3_SENSITIVE_KEYS)
        else:
            repo.delete(key)
    return config
