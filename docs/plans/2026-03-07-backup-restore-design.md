# Backup & Restore Design

**Date:** 2026-03-07
**Status:** Approved

## Overview

Full-system backup and restore for FluxFinance. Backs up SQLite database + zvec collections as a `.zip` archive. Supports local storage and S3-compatible remote storage (Cloudflare R2, AWS S3, MinIO).

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scope | Full-system (not per-user) | Simpler, copies entire DB + zvec |
| File format | `.zip` | Most universally supported |
| Remote storage | S3-compatible (boto3) | Works with R2/S3/MinIO, cheap, standard |
| Local fallback | Yes, `/data/backups/` | Always works without config |
| SQLite backup method | `connection.backup()` API | Consistent snapshot, safe with WAL mode |
| Encryption | `FLUX_SECRET_KEY` env var | Single key encrypts all sensitive config in SQLite |
| Restore safety | Auto-backup before restore | Non-optional, prevents catastrophic mistakes |
| Interfaces | Bot + Web UI + Scheduled | All three |
| Config storage | S3 credentials encrypted in SQLite | Configurable via Web UI at runtime |

## Architecture

### Core Domain

Follows existing Use Case + Repository + UoW patterns.

#### Backup Metadata Model

```python
class BackupMetadata(BaseModel):
    id: str                          # UUID
    filename: str                    # e.g. "flux-backup-2026-03-07T020000.zip"
    size_bytes: int
    created_at: datetime
    storage: Literal["local", "s3"]
    s3_key: str | None = None
    local_path: str | None = None
```

No SQLite table for metadata. Derive backup list by listing local directory + S3 bucket prefix.

#### Encryption Service

Single env var `FLUX_SECRET_KEY` used to encrypt sensitive config (S3 credentials, future API tokens) stored in SQLite.

```python
# Uses cryptography.Fernet with PBKDF2 key derivation
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
```

A `system_config` table in SQLite stores key-value pairs. Sensitive values are Fernet-encrypted before storage.

#### Storage Provider Protocol

```python
class BackupStorageProvider(Protocol):
    async def upload(self, file_path: Path, key: str) -> str: ...
    async def download(self, key: str, dest: Path) -> Path: ...
    async def list_backups(self) -> list[BackupMetadata]: ...
    async def delete(self, key: str) -> None: ...
```

Two implementations:
- `LocalStorageProvider` -- reads/writes `/data/backups/`
- `S3StorageProvider` -- uses `boto3` with S3-compatible endpoint

#### Use Cases

| Use Case | Description |
|---|---|
| `CreateBackup` | SQLite `backup()` + copy zvec -> zip -> upload to storage(s) |
| `RestoreBackup` | Auto-backup current -> download zip -> replace SQLite + zvec |
| `ListBackups` | List from local + S3, deduplicate, sort by date |
| `DeleteBackup` | Delete from specified storage |
| `ConfigureScheduledBackup` | Create/update bot_scheduled_tasks for auto-backups |

### Backup Creation Flow

1. `connection.backup()` -> temp SQLite file (consistent snapshot)
2. `shutil.copytree()` -> temp copy of zvec directory
3. Zip both into `flux-backup-{timestamp}.zip`
4. Upload to local and/or S3 based on config
5. Clean up temp files
6. Apply retention policy (delete old backups beyond limit)

### Restore Flow

1. Create auto-backup of current data (reuse `CreateBackup`)
2. Download/copy the target backup zip to temp directory
3. Extract and validate: `PRAGMA integrity_check` on SQLite, verify zvec collections
4. Acquire exclusive lock / signal to stop writes
5. Replace SQLite DB + zvec directory
6. Signal app to reconnect/restart

## Interface Layer

### API Server

```
POST   /api/backups              # Create backup (?storage=local|s3|both)
GET    /api/backups              # List all backups
GET    /api/backups/{id}/download # Download backup file
POST   /api/backups/restore      # Restore (multipart file upload OR {backup_id})
DELETE /api/backups/{id}         # Delete a backup
GET    /api/backups/config       # Get backup settings
PUT    /api/backups/config       # Update backup settings
```

### MCP Server

`register_backup_tools()`:
- `create_backup(storage?)`
- `list_backups()`
- `restore_backup(backup_id)`

### Bot Commands

**`/backup`:**
- S3 configured -> inline keyboard: "Send to Telegram" | "Upload to S3"
- No S3 -> send `.zip` via `send_document` + advise enabling S3 in Web UI

**`/restore`:**
- S3 configured -> list S3 backups as inline keyboard + "Upload file" option
- No S3 -> prompt user to send a `.zip` file
- Always confirms: "This will replace all data. Auto-backup created first."

**`/onboard` addition:**
- Step: "How often should I auto-backup? Daily / Weekly / Never"
- Step: "Where to store? Local only / S3 (configure in Settings)"

### Web UI

New **"Data"** tab in Settings page:
- **Backup section**: "Create Backup Now" button, backup list table (date, size, storage, download/delete)
- **Restore section**: File upload dropzone OR pick from backup list
- **Schedule section**: Frequency dropdown + retention inputs
- **S3 Config section**: Endpoint, bucket, region, access key, secret key fields (keys encrypted via `FLUX_SECRET_KEY`)

## Configuration

### Environment Variables

```env
# Required for encryption (must be set)
FLUX_SECRET_KEY=user-generated-secret

# Backup local storage
BACKUP_LOCAL_DIR=/data/backups       # default
BACKUP_LOCAL_RETENTION=7             # keep last N local backups
BACKUP_S3_RETENTION=30               # keep last N S3 backups
```

S3 credentials stored encrypted in SQLite `system_config` table, configurable via Web UI.

### New Dependencies

- `boto3` -- S3-compatible storage (lazy import, only when S3 configured)
- `cryptography` -- Fernet encryption for sensitive config

### New Files

```
packages/core/src/flux_core/
  models/backup.py                         # BackupMetadata model
  use_cases/backup/
    create_backup.py
    restore_backup.py
    list_backups.py
    delete_backup.py
    configure_scheduled_backup.py
  services/
    encryption.py                          # Fernet encrypt/decrypt service
    storage/
      protocol.py                          # BackupStorageProvider protocol
      local.py                             # LocalStorageProvider
      s3.py                                # S3StorageProvider
  sqlite/migrations/NNN_system_config.sql  # system_config table

packages/api-server/src/flux_api/routes/
  backups.py                               # REST endpoints

packages/mcp-server/src/flux_mcp/tools/
  backup.py                                # register_backup_tools()

packages/agent-bot/src/flux_bot/
  commands/backup.py                       # /backup, /restore handlers

packages/web-ui/src/
  pages/settings/DataTab.tsx               # New settings tab
```

### SQLite Migration: system_config table

```sql
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Future: Runtime Configuration (Separate Story)

Moving `TELEGRAM_BOT_TOKEN`, `CLAUDE_AUTH_TOKEN`, `CLAUDE_MODEL`, `TELEGRAM_ALLOW_FROM` to encrypted SQLite config is a separate feature that builds on the `FLUX_SECRET_KEY` + `system_config` infrastructure introduced here.
