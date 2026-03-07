"""Backup metadata model."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BackupMetadata(BaseModel):
    id: str
    filename: str
    size_bytes: int
    created_at: datetime
    storage: Literal["local", "s3"]
    s3_key: str | None = None
    local_path: str | None = None
