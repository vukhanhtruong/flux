# Backup Notification via Telegram — Design

## Overview

After a backup completes, notify the triggering user via Telegram with backup details. For local backups under 50MB, attach the `.zip` file so users can download directly. For S3 backups, send a text-only notification.

## Requirements

1. **All backups** (scheduled, MCP, API) are eligible for notification
2. **API-triggered backups** skip notification — user sees result in web UI
3. **Notify the triggering user** — for scheduled backups, the user who set up the schedule
4. **Local backups < 50MB**: attach the `.zip` file to the Telegram message
5. **Local backups >= 50MB**: text notification + "download from web UI"
6. **S3 backups**: text notification only
7. **S3 tip**: when storage is local and S3 is not configured, show a tip suggesting S3 setup via web UI

## Architecture

Event-driven via the existing EventBus (in-process pub/sub):

```
CreateBackup.execute()
    ↓ (success)
EventBus.emit(BackupCompleted)
    ↓
BackupNotificationHandler.handle()
    ↓
TelegramChannel.send_document() or send_message()
```

## Design

### 1. New Event: `BackupCompleted`

Added to `packages/core/src/flux_core/events/events.py`:

```python
@dataclass(frozen=True)
class BackupCompleted(Event):
    filename: str
    size_bytes: int
    storage: str           # "local" or "s3" (one event per storage)
    user_id: str           # who triggered it (required)
    local_path: str | None # file path for attachment (local only)
```

When `storage="both"`, `CreateBackup` emits **two separate events** — one per storage that succeeded. This keeps subscriber logic clean: local event = try to attach file, s3 event = text only.

### 2. `CreateBackup` Changes

- Add optional `event_bus: EventBus | None` and `user_id: str | None` to `__init__`
- After successful upload(s) and retention, emit `BackupCompleted` for each storage
- No event emitted if `event_bus` is None

| Caller | Passes event_bus? | Passes user_id? |
|--------|:-:|:-:|
| MCP `create_backup` tool | Yes | Yes |
| Scheduled task (via MCP) | Yes | Yes |
| API `POST /backups/` | No | No |

### 3. `TelegramChannel.send_document()`

New method on `TelegramChannel`:

```python
async def send_document(self, platform_id: str, file_path: str, caption: str | None = None) -> None:
```

- Uses `self._app.bot.send_document()` from python-telegram-bot
- Caption converted via `convert_markdown()`, `parse_mode=MarkdownV2`
- Same retry logic as `_send_with_retry`

Also added to `Channel` base class as optional method (default raises `NotImplementedError`).

### 4. `BackupNotificationHandler`

New module: `packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py`

```python
class BackupNotificationHandler:
    def __init__(self, channels: dict, s3_configured_fn: Callable[[], bool]):
        self.channels = channels
        self._s3_configured = s3_configured_fn

    async def handle(self, event: BackupCompleted) -> None:
        ...
```

Logic:
1. Parse `event.user_id` to get channel name + platform_id (e.g., `"tg:12345"` -> `"telegram"`, `"12345"`)
2. Look up channel handler from `self.channels`
3. Format notification message
4. If local + file < 50MB: `channel.send_document()` with caption
5. If local + file >= 50MB: `channel.send_message()` with download hint
6. If S3: `channel.send_message()` with text only
7. If local and S3 not configured: append tip about configuring S3 in web UI

`s3_configured_fn` is a callable (not a static bool) because S3 can be configured at runtime via the web UI.

Registered during orchestrator startup:
```python
event_bus.subscribe(BackupCompleted, backup_handler.handle)
```

### 5. Message Templates

**Local, file attached (< 50MB):**
```
Backup completed
**File**: flux-backup-2026-03-14T020000.zip
**Size**: 4.2 MB
**Storage**: local

Tip: You can configure S3 backup in the web UI for cloud storage.
```
(Tip only when S3 not configured. Sent as document caption.)

**Local, too large (>= 50MB):**
```
Backup completed
**File**: flux-backup-2026-03-14T020000.zip
**Size**: 62.1 MB
**Storage**: local

File too large to attach. Download from the web UI.

Tip: You can configure S3 backup in the web UI for cloud storage.
```
(Tip only when S3 not configured.)

**S3:**
```
Backup completed
**File**: flux-backup-2026-03-14T020000.zip
**Size**: 4.2 MB
**Storage**: s3
```

Size formatted as human-readable (bytes -> KB/MB/GB).

## Files Changed

| File | Change |
|------|--------|
| `packages/core/src/flux_core/events/events.py` | Add `BackupCompleted` event |
| `packages/core/src/flux_core/use_cases/backup/create_backup.py` | Accept optional `event_bus` + `user_id`, emit events |
| `packages/agent-bot/src/flux_bot/channels/base.py` | Add `send_document()` optional method |
| `packages/agent-bot/src/flux_bot/channels/telegram.py` | Implement `send_document()` |
| `packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py` | New — notification handler |
| `packages/agent-bot/src/flux_bot/main.py` | Register `BackupNotificationHandler` subscriber |
| `packages/mcp-server/src/flux_mcp/tools/backup_tools.py` | Pass `event_bus` + `user_id` to `CreateBackup` |
