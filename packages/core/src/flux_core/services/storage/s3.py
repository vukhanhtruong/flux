"""S3-compatible backup storage provider."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import boto3

from flux_core.models.backup import BackupMetadata


class S3StorageProvider:
    _PREFIX = "backups/"

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "auto",
    ):
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    async def upload(self, file_path: Path, key: str) -> str:
        s3_key = f"{self._PREFIX}{key}"
        self._client.upload_file(str(file_path), self._bucket, s3_key)
        return s3_key

    async def download(self, key: str, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        filename = key.split("/")[-1]
        target = dest / filename
        self._client.download_file(self._bucket, key, str(target))
        return target

    async def list_backups(self) -> list[BackupMetadata]:
        response = self._client.list_objects_v2(
            Bucket=self._bucket, Prefix=self._PREFIX
        )
        contents = response.get("Contents", [])
        backups = []
        for obj in contents:
            filename = obj["Key"].split("/")[-1]
            if not filename.endswith(".zip"):
                continue
            backups.append(
                BackupMetadata(
                    id=str(uuid4()),
                    filename=filename,
                    size_bytes=obj["Size"],
                    created_at=obj["LastModified"],
                    storage="s3",
                    s3_key=obj["Key"],
                )
            )
        return sorted(backups, key=lambda b: b.created_at, reverse=True)

    async def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
