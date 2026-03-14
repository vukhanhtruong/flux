# Backup Notification via Telegram — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Notify users via Telegram when backups complete, attaching the zip file for local backups under 50MB.

**Architecture:** Event-driven via existing EventBus. `CreateBackup` emits `BackupCompleted` events, a new `BackupNotificationHandler` in agent-bot subscribes and sends Telegram messages (with file attachment for local backups).

**Tech Stack:** Python 3.12, flux_core EventBus, python-telegram-bot, pytest

**Design doc:** `docs/plans/2026-03-14-backup-notification-design.md`

---

### Task 1: Add `BackupCompleted` Event

**Files:**
- Modify: `packages/core/src/flux_core/events/events.py:67-70` (append after `ScheduledTaskDue`)
- Test: `packages/core/tests/test_events/test_bus.py` (add test)

**Step 1: Write the failing test**

In `packages/core/tests/test_events/test_bus.py`, add:

```python
from flux_core.events.events import BackupCompleted
from datetime import datetime, UTC


async def test_backup_completed_event_emitted():
    """BackupCompleted event is emitted and received by subscriber."""
    from flux_core.events.bus import EventBus

    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(BackupCompleted, handler)
    event = BackupCompleted(
        timestamp=datetime.now(UTC),
        filename="flux-backup-2026-03-14T020000.zip",
        size_bytes=4_200_000,
        storage="local",
        user_id="tg:12345",
        local_path="/data/backups/flux-backup-2026-03-14T020000.zip",
    )
    await bus.emit(event)

    assert len(received) == 1
    assert received[0].filename == "flux-backup-2026-03-14T020000.zip"
    assert received[0].storage == "local"
    assert received[0].user_id == "tg:12345"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_events/test_bus.py::test_backup_completed_event_emitted -v`
Expected: FAIL with `ImportError: cannot import name 'BackupCompleted'`

**Step 3: Write minimal implementation**

In `packages/core/src/flux_core/events/events.py`, append after `ScheduledTaskDue`:

```python
@dataclass(frozen=True)
class BackupCompleted(Event):
    filename: str
    size_bytes: int
    storage: str  # "local" or "s3"
    user_id: str
    local_path: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `cd packages/core && python -m pytest tests/test_events/test_bus.py::test_backup_completed_event_emitted -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/events/events.py packages/core/tests/test_events/test_bus.py
git commit -m "feat: add BackupCompleted event"
```

---

### Task 2: `CreateBackup` Emits `BackupCompleted` Events

**Files:**
- Modify: `packages/core/src/flux_core/use_cases/backup/create_backup.py`
- Test: `packages/core/tests/test_use_cases/test_backup.py`

**Step 1: Write the failing tests**

In `packages/core/tests/test_use_cases/test_backup.py`, add:

```python
from flux_core.events.bus import EventBus
from flux_core.events.events import BackupCompleted


async def test_create_backup_emits_event_local(tmp_path):
    """CreateBackup emits BackupCompleted event for local storage."""
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    db = _mock_db(db_path)

    local_provider = AsyncMock()
    local_provider.upload.return_value = "/data/backups/flux-backup-test.zip"

    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(BackupCompleted, handler)

    uc = CreateBackup(
        db=db, zvec_path=zvec_path,
        local_provider=local_provider, s3_provider=None,
        event_bus=bus, user_id="tg:12345",
    )
    await uc.execute(storage="local")

    assert len(received) == 1
    assert received[0].storage == "local"
    assert received[0].user_id == "tg:12345"
    assert received[0].local_path == "/data/backups/flux-backup-test.zip"


async def test_create_backup_emits_two_events_for_both(tmp_path):
    """CreateBackup emits two BackupCompleted events when storage='both'."""
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    db = _mock_db(db_path)

    local_provider = AsyncMock()
    local_provider.upload.return_value = "/data/backups/flux-backup-test.zip"
    s3_provider = AsyncMock()
    s3_provider.upload.return_value = "backups/flux-backup-test.zip"

    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(BackupCompleted, handler)

    uc = CreateBackup(
        db=db, zvec_path=zvec_path,
        local_provider=local_provider, s3_provider=s3_provider,
        event_bus=bus, user_id="tg:12345",
    )
    await uc.execute(storage="both")

    assert len(received) == 2
    storages = {e.storage for e in received}
    assert storages == {"local", "s3"}


async def test_create_backup_no_event_without_bus(tmp_path):
    """CreateBackup does not fail when event_bus is None."""
    db_path = _make_test_db(tmp_path)
    zvec_path = _make_test_zvec(tmp_path)
    db = _mock_db(db_path)

    local_provider = AsyncMock()
    local_provider.upload.return_value = "flux-backup-test.zip"

    uc = CreateBackup(
        db=db, zvec_path=zvec_path,
        local_provider=local_provider, s3_provider=None,
    )
    result = await uc.execute(storage="local")
    assert result is not None  # Works fine without event_bus
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py::test_create_backup_emits_event_local tests/test_use_cases/test_backup.py::test_create_backup_emits_two_events_for_both tests/test_use_cases/test_backup.py::test_create_backup_no_event_without_bus -v`
Expected: FAIL with `TypeError: CreateBackup.__init__() got an unexpected keyword argument 'event_bus'`

**Step 3: Write minimal implementation**

Modify `packages/core/src/flux_core/use_cases/backup/create_backup.py`:

1. Add imports at top:
```python
from flux_core.events.bus import EventBus
from flux_core.events.events import BackupCompleted
```

2. Add `event_bus` and `user_id` to `__init__`:
```python
def __init__(
    self,
    db: Database,
    zvec_path: str,
    local_provider: LocalStorageProvider | None = None,
    s3_provider: S3StorageProvider | None = None,
    local_retention: int | None = None,
    s3_retention: int | None = None,
    event_bus: EventBus | None = None,
    user_id: str | None = None,
):
    self._db = db
    self._zvec_path = zvec_path
    self._local = local_provider
    self._s3 = s3_provider
    self._local_retention = local_retention
    self._s3_retention = s3_retention
    self._event_bus = event_bus
    self._user_id = user_id
```

3. Add `_emit_event` helper and call it after each successful upload in `execute()`. After retention is applied (line 99), before `return result_meta`:

```python
async def _emit_event(
    self, filename: str, size_bytes: int, storage: str, local_path: str | None
) -> None:
    if self._event_bus and self._user_id:
        event = BackupCompleted(
            timestamp=datetime.now(UTC),
            filename=filename,
            size_bytes=size_bytes,
            storage=storage,
            user_id=self._user_id,
            local_path=local_path,
        )
        await self._event_bus.emit(event)
```

4. In `execute()`, collect events to emit, then emit after retention:

Replace the upload section (lines 77-101) with logic that tracks each successful upload and emits events after `_apply_retention()`. Key change: after each upload, store the event params. After retention, emit all events. Then return `result_meta`.

```python
        # 4. Upload to storage(s)
        result_meta = None
        pending_events = []
        if storage in ("local", "both") and self._local:
            key = await self._local.upload(zip_path, filename)
            size = zip_path.stat().st_size
            result_meta = BackupMetadata(
                id=timestamp,
                filename=filename,
                size_bytes=size,
                created_at=datetime.now(UTC),
                storage="local",
                local_path=key,
            )
            pending_events.append(("local", size, key))
        if storage in ("s3", "both") and self._s3:
            key = await self._s3.upload(zip_path, filename)
            size = zip_path.stat().st_size
            result_meta = BackupMetadata(
                id=timestamp,
                filename=filename,
                size_bytes=size,
                created_at=datetime.now(UTC),
                storage="s3",
                s3_key=key,
            )
            pending_events.append(("s3", size, None))

    await self._apply_retention()

    for evt_storage, evt_size, evt_local_path in pending_events:
        await self._emit_event(filename, evt_size, evt_storage, evt_local_path)

    return result_meta
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup.py -v`
Expected: ALL PASS (including existing tests — they don't pass event_bus, so no events emitted)

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/use_cases/backup/create_backup.py packages/core/tests/test_use_cases/test_backup.py
git commit -m "feat: CreateBackup emits BackupCompleted events"
```

---

### Task 3: Add `send_document()` to Channel Base and TelegramChannel

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/channels/base.py:19-22`
- Modify: `packages/agent-bot/src/flux_bot/channels/telegram.py`
- Test: `packages/agent-bot/tests/test_channels/test_telegram.py`

**Step 1: Write the failing tests**

In `packages/agent-bot/tests/test_channels/test_telegram.py`, add:

```python
async def test_send_document_sends_file(tmp_path):
    """send_document sends a file via Telegram bot.send_document."""
    ch, _, _ = _make_channel()
    ch._app.bot.send_document = AsyncMock()

    test_file = tmp_path / "test.zip"
    test_file.write_bytes(b"fake-zip-content")

    await ch.send_document(platform_id="12345", file_path=str(test_file), caption="Backup done")

    ch._app.bot.send_document.assert_called_once()
    call_kwargs = ch._app.bot.send_document.call_args[1]
    assert call_kwargs["chat_id"] == 12345
    assert call_kwargs["parse_mode"] == "MarkdownV2"


async def test_send_document_without_caption(tmp_path):
    """send_document works without a caption."""
    ch, _, _ = _make_channel()
    ch._app.bot.send_document = AsyncMock()

    test_file = tmp_path / "test.zip"
    test_file.write_bytes(b"fake-zip-content")

    await ch.send_document(platform_id="12345", file_path=str(test_file))

    ch._app.bot.send_document.assert_called_once()
    call_kwargs = ch._app.bot.send_document.call_args[1]
    assert call_kwargs["chat_id"] == 12345
    assert "caption" not in call_kwargs or call_kwargs["caption"] is None


async def test_send_document_retries_on_timeout(tmp_path):
    """send_document retries on TimedOut errors."""
    from telegram.error import TimedOut

    ch, _, _ = _make_channel()
    call_count = 0

    async def flaky_send(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise TimedOut()

    ch._app.bot.send_document = flaky_send

    test_file = tmp_path / "test.zip"
    test_file.write_bytes(b"fake-zip-content")

    await ch.send_document(platform_id="12345", file_path=str(test_file))
    assert call_count == 3


async def test_send_document_raises_if_not_started(tmp_path):
    """send_document raises RuntimeError when bot is not initialized."""
    import pytest

    ch, _, _ = _make_channel()
    ch._app = None

    test_file = tmp_path / "test.zip"
    test_file.write_bytes(b"fake-zip-content")

    with pytest.raises(RuntimeError, match="not initialized"):
        await ch.send_document(platform_id="12345", file_path=str(test_file))
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/agent-bot && python -m pytest tests/test_channels/test_telegram.py::test_send_document_sends_file -v`
Expected: FAIL with `AttributeError: 'TelegramChannel' object has no attribute 'send_document'`

**Step 3: Write minimal implementation**

Add to `packages/agent-bot/src/flux_bot/channels/base.py` after `send_outbound`:

```python
async def send_document(
    self, platform_id: str, file_path: str, caption: str | None = None
) -> None:
    """Send a file to a user. Subclasses must override to enable file sending."""
    raise NotImplementedError(f"{type(self).__name__} does not implement send_document")
```

Add to `packages/agent-bot/src/flux_bot/channels/telegram.py` after `send_outbound`:

```python
async def send_document(
    self, platform_id: str, file_path: str, caption: str | None = None
) -> None:
    """Send a file to a Telegram user with optional caption."""
    if not self._app:
        raise RuntimeError("Telegram bot not initialized — cannot send document")
    kwargs: dict = {
        "chat_id": int(platform_id),
        "document": open(file_path, "rb"),
    }
    if caption:
        kwargs["caption"] = convert_markdown(caption)
        kwargs["parse_mode"] = "MarkdownV2"
    delay = 1.0
    for attempt in range(_MAX_SEND_RETRIES):
        try:
            await self._app.bot.send_document(**kwargs)
            return
        except (TimedOut, NetworkError) as e:
            if attempt == _MAX_SEND_RETRIES - 1:
                raise
            logger.warning(
                f"Telegram send_document to {platform_id} failed "
                f"(attempt {attempt + 1}), retrying in {delay}s: {e}"
            )
            await asyncio.sleep(delay)
            delay *= 2
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/agent-bot && python -m pytest tests/test_channels/test_telegram.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/agent-bot/src/flux_bot/channels/base.py packages/agent-bot/src/flux_bot/channels/telegram.py packages/agent-bot/tests/test_channels/test_telegram.py
git commit -m "feat: add send_document to Channel base and TelegramChannel"
```

---

### Task 4: Create `BackupNotificationHandler`

**Files:**
- Create: `packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py`
- Test: `packages/agent-bot/tests/test_orchestrator/test_backup_notify.py`

**Step 1: Write the failing tests**

Create `packages/agent-bot/tests/test_orchestrator/test_backup_notify.py`:

```python
"""Tests for BackupNotificationHandler."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flux_core.events.events import BackupCompleted


def _make_event(storage="local", size_bytes=4_200_000, user_id="tg:12345", local_path=None):
    return BackupCompleted(
        timestamp=datetime.now(UTC),
        filename="flux-backup-2026-03-14T020000.zip",
        size_bytes=size_bytes,
        storage=storage,
        user_id=user_id,
        local_path=local_path or ("/data/backups/flux-backup-2026-03-14T020000.zip" if storage == "local" else None),
    )


def _make_handler(s3_configured=False):
    from flux_bot.orchestrator.backup_notify import BackupNotificationHandler

    channel = AsyncMock()
    channels = {"telegram": channel}
    handler = BackupNotificationHandler(
        channels=channels,
        s3_configured_fn=lambda: s3_configured,
    )
    return handler, channel


async def test_local_backup_small_sends_document():
    """Local backup under 50MB sends file attachment."""
    handler, channel = _make_handler(s3_configured=False)
    event = _make_event(storage="local", size_bytes=4_200_000, local_path="/data/backups/test.zip")

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=4_200_000)
        await handler.handle(event)

    channel.send_document.assert_called_once()
    call_kwargs = channel.send_document.call_args[1]
    assert call_kwargs["platform_id"] == "12345"
    assert call_kwargs["file_path"] == "/data/backups/test.zip"
    assert "Backup completed" in call_kwargs["caption"]
    assert "S3" in call_kwargs["caption"]  # S3 tip shown because S3 not configured


async def test_local_backup_small_no_s3_tip_when_configured():
    """Local backup does not show S3 tip when S3 is configured."""
    handler, channel = _make_handler(s3_configured=True)
    event = _make_event(storage="local", size_bytes=4_200_000, local_path="/data/backups/test.zip")

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=4_200_000)
        await handler.handle(event)

    channel.send_document.assert_called_once()
    caption = channel.send_document.call_args[1]["caption"]
    assert "S3" not in caption


async def test_local_backup_large_sends_text_only():
    """Local backup >= 50MB sends text message without file."""
    handler, channel = _make_handler(s3_configured=False)
    event = _make_event(
        storage="local", size_bytes=62_000_000,
        local_path="/data/backups/test.zip",
    )

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=62_000_000)
        await handler.handle(event)

    channel.send_document.assert_not_called()
    channel.send_message.assert_called_once()
    text = channel.send_message.call_args[0][1]
    assert "too large" in text.lower()
    assert "web UI" in text


async def test_s3_backup_sends_text_only():
    """S3 backup sends text-only notification."""
    handler, channel = _make_handler()
    event = _make_event(storage="s3")

    await handler.handle(event)

    channel.send_document.assert_not_called()
    channel.send_message.assert_called_once()
    text = channel.send_message.call_args[0][1]
    assert "Backup completed" in text
    assert "s3" in text.lower()


async def test_unknown_channel_prefix_skips_silently():
    """Event with unrecognized user_id prefix is skipped."""
    handler, channel = _make_handler()
    event = _make_event(user_id="wa:99999")  # No whatsapp channel registered

    await handler.handle(event)

    channel.send_document.assert_not_called()
    channel.send_message.assert_not_called()


async def test_local_backup_missing_file_sends_text():
    """Local backup where file is missing on disk sends text-only."""
    handler, channel = _make_handler()
    event = _make_event(storage="local", local_path="/data/backups/gone.zip")

    with patch("pathlib.Path.exists", return_value=False):
        await handler.handle(event)

    channel.send_document.assert_not_called()
    channel.send_message.assert_called_once()


async def test_format_size_human_readable():
    """Size formatting produces human-readable output."""
    from flux_bot.orchestrator.backup_notify import _format_size

    assert _format_size(500) == "500 B"
    assert _format_size(1536) == "1.5 KB"
    assert _format_size(4_200_000) == "4.0 MB"
    assert _format_size(1_500_000_000) == "1.4 GB"
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_backup_notify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'flux_bot.orchestrator.backup_notify'`

**Step 3: Write minimal implementation**

Create `packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py`:

```python
"""Backup notification handler — sends Telegram messages when backups complete."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import structlog

from flux_core.events.events import BackupCompleted
from flux_core.models.user_profile import _CHANNEL_PREFIXES

logger = structlog.get_logger(__name__)

CHANNEL_PREFIXES = {v: k for k, v in _CHANNEL_PREFIXES.items()}

_MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024  # 50MB


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024 or unit == "GB":
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def _parse_channel_prefix(user_id: str) -> tuple[str | None, str]:
    """Parse 'tg:12345' into ('telegram', '12345')."""
    if ":" in user_id:
        prefix, platform_id = user_id.split(":", 1)
        return CHANNEL_PREFIXES.get(prefix), platform_id
    return None, user_id


class BackupNotificationHandler:
    def __init__(
        self,
        channels: dict,
        s3_configured_fn: Callable[[], bool],
    ):
        self.channels = channels
        self._s3_configured = s3_configured_fn

    async def handle(self, event: BackupCompleted) -> None:
        """Handle BackupCompleted event — send notification to triggering user."""
        channel_name, platform_id = _parse_channel_prefix(event.user_id)
        channel = self.channels.get(channel_name) if channel_name else None

        if channel is None:
            logger.warning(
                "No channel for backup notification",
                user_id=event.user_id,
                channel=channel_name,
            )
            return

        size_str = _format_size(event.size_bytes)
        base_msg = (
            f"Backup completed\n"
            f"**File**: {event.filename}\n"
            f"**Size**: {size_str}\n"
            f"**Storage**: {event.storage}"
        )

        s3_tip = ""
        if event.storage == "local" and not self._s3_configured():
            s3_tip = "\n\nTip: You can configure S3 backup in the web UI for cloud storage."

        if event.storage == "local" and event.local_path:
            file_path = Path(event.local_path)
            if file_path.exists() and file_path.stat().st_size < _MAX_ATTACHMENT_SIZE:
                caption = base_msg + s3_tip
                await channel.send_document(
                    platform_id=platform_id,
                    file_path=str(file_path),
                    caption=caption,
                )
                return

            # File too large or missing — text-only
            too_large_msg = base_msg + "\n\nFile too large to attach. Download from the web UI."
            await channel.send_message(platform_id, too_large_msg + s3_tip)
            return

        # S3 storage — text only
        await channel.send_message(platform_id, base_msg)
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_backup_notify.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py packages/agent-bot/tests/test_orchestrator/test_backup_notify.py
git commit -m "feat: add BackupNotificationHandler for Telegram notifications"
```

---

### Task 5: Wire Up — MCP Server Passes `event_bus` and `user_id` to `CreateBackup`

**Files:**
- Modify: `packages/mcp-server/src/flux_mcp/tools/backup_tools.py`
- Modify: `packages/mcp-server/src/flux_mcp/server.py:77`
- Test: `packages/mcp-server/tests/test_backup_tools.py`

**Step 1: Write the failing test**

In `packages/mcp-server/tests/test_backup_tools.py`, add:

```python
async def test_create_backup_passes_event_bus_and_user_id():
    """create_backup tool passes event_bus and user_id to CreateBackup."""
    meta = BackupMetadata(
        id="2026-03-14T120000",
        filename="flux-backup-2026-03-14T120000.zip",
        size_bytes=1024,
        created_at=datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC),
        storage="local",
        local_path="/data/backups/flux-backup-2026-03-14T120000.zip",
    )

    mock_db = MagicMock()
    mock_local_storage = MagicMock()
    mock_event_bus = MagicMock()

    with patch(
        "flux_mcp.tools.backup_tools.CreateBackup"
    ) as MockCreateBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = meta
        MockCreateBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _create_backup_impl

        result = await _create_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=mock_local_storage,
            s3_storage=None,
            storage="local",
            event_bus=mock_event_bus,
            user_id="tg:12345",
        )

    assert result["status"] == "ok"
    MockCreateBackup.assert_called_once_with(
        mock_db, "/data/zvec", mock_local_storage, None,
        event_bus=mock_event_bus, user_id="tg:12345",
    )
```

**Step 2: Run test to verify it fails**

Run: `cd packages/mcp-server && python -m pytest tests/test_backup_tools.py::test_create_backup_passes_event_bus_and_user_id -v`
Expected: FAIL with `TypeError: _create_backup_impl() got an unexpected keyword argument 'event_bus'`

**Step 3: Write minimal implementation**

Modify `packages/mcp-server/src/flux_mcp/tools/backup_tools.py`:

1. Update `_create_backup_impl` signature to accept `event_bus` and `user_id`:

```python
async def _create_backup_impl(
    db: Database,
    zvec_path: str,
    local_storage,
    s3_storage,
    storage: str = "auto",
    event_bus=None,
    user_id: str | None = None,
) -> dict:
    """Internal implementation for create_backup tool."""
    try:
        if storage == "auto":
            storage = "s3" if s3_storage is not None else "local"
        uc = CreateBackup(
            db, zvec_path, local_storage, s3_storage,
            event_bus=event_bus, user_id=user_id,
        )
        meta = await uc.execute(storage=storage)
        return {
            "status": "ok",
            "filename": meta.filename,
            "size_bytes": meta.size_bytes,
            "storage": meta.storage,
            "created_at": str(meta.created_at),
        }
    except (ValueError, OSError) as exc:
        return {"status": "error", "error": str(exc)}
```

2. Update `register_backup_tools` to accept `get_event_bus` and `get_session_user_id`:

```python
def register_backup_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_local_storage: Callable,
    get_s3_storage: Callable,
    get_event_bus: Callable | None = None,
    get_session_user_id: Callable | None = None,
):
```

3. Update the `create_backup` tool closure to pass them through:

```python
    @mcp.tool()
    async def create_backup(storage: str = "auto") -> dict:
        """Create a backup of the database and vector store.

        Args:
            storage: Where to store — "auto" (S3 if configured, else local), "local", "s3", or "both".
        """
        zvec_path = os.getenv("ZVEC_PATH", "/data/zvec")
        event_bus = get_event_bus() if get_event_bus else None
        user_id = get_session_user_id() if get_session_user_id else None
        return await _create_backup_impl(
            db=get_db(),
            zvec_path=zvec_path,
            local_storage=get_local_storage(),
            s3_storage=get_s3_storage(),
            storage=storage,
            event_bus=event_bus,
            user_id=user_id,
        )
```

4. Update `packages/mcp-server/src/flux_mcp/server.py` line 77 to pass the new params:

```python
register_backup_tools(mcp, get_db, get_local_storage, get_s3_storage, get_event_bus, get_session_user_id)
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/mcp-server && python -m pytest tests/test_backup_tools.py -v`
Expected: ALL PASS (existing tests still pass because `event_bus` and `user_id` default to None)

**Step 5: Commit**

```bash
git add packages/mcp-server/src/flux_mcp/tools/backup_tools.py packages/mcp-server/src/flux_mcp/server.py packages/mcp-server/tests/test_backup_tools.py
git commit -m "feat: pass event_bus and user_id through MCP backup tools"
```

---

### Task 6: Wire Up — Agent Bot Subscribes to `BackupCompleted`

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/main.py`

**Step 1: Write the failing test**

This is wiring-only (no new logic to unit test). We verify via integration: the import works and the handler can be instantiated.

In `packages/agent-bot/tests/test_orchestrator/test_backup_notify.py`, add:

```python
async def test_handler_can_be_constructed_with_s3_check():
    """BackupNotificationHandler accepts a callable for s3_configured_fn."""
    from flux_bot.orchestrator.backup_notify import BackupNotificationHandler

    handler = BackupNotificationHandler(
        channels={"telegram": AsyncMock()},
        s3_configured_fn=lambda: False,
    )
    assert handler is not None
```

**Step 2: Run test**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_backup_notify.py::test_handler_can_be_constructed_with_s3_check -v`
Expected: PASS (already works from Task 4)

**Step 3: Write the wiring in main.py**

In `packages/agent-bot/src/flux_bot/main.py`, add the following after the `scheduler_worker` setup (around line 100) and before the `asyncio.create_task` calls:

1. Add imports at top:
```python
from flux_core.events.bus import EventBus
from flux_core.events.events import BackupCompleted
from flux_bot.orchestrator.backup_notify import BackupNotificationHandler
```

2. Add after scheduler_worker setup:
```python
    # Backup notification subscriber
    event_bus = EventBus()
    backup_notifier = BackupNotificationHandler(
        channels=channels,
        s3_configured_fn=lambda: _is_s3_configured(db),
    )
    event_bus.subscribe(BackupCompleted, backup_notifier.handle)
```

3. Add helper function before `main()`:
```python
def _is_s3_configured(db: Database) -> bool:
    """Check if S3 backup is configured."""
    try:
        from flux_core.services.encryption import EncryptionService
        from flux_core.sqlite.system_config_repo import SqliteSystemConfigRepository
        enc = EncryptionService.from_env()
        config_repo = SqliteSystemConfigRepository(db.connection(), enc)
        endpoint = config_repo.get("s3_endpoint")
        bucket = config_repo.get("s3_bucket")
        access_key = config_repo.get("s3_access_key")
        secret_key = config_repo.get("s3_secret_key")
        return all([endpoint, bucket, access_key, secret_key])
    except (ValueError, ImportError):
        return False
```

**Note:** The EventBus instance created here in agent-bot is separate from the one in the MCP server. Since the MCP server runs as a subprocess (spawned by `ClaudeRunner`), the events are emitted in the MCP server's process. The agent-bot EventBus subscribes in its own process. This means **the event must be emitted in the MCP server process and the notification handler must also run there**.

**Wait — this is a cross-process boundary issue.** The MCP server is a separate subprocess. The agent-bot's EventBus cannot receive events from it.

**Revised approach:** The notification should happen **in the MCP server process** directly, not via EventBus across processes. Instead:

1. `CreateBackup` emits `BackupCompleted` on the EventBus **within the MCP server process**
2. The MCP server registers a lightweight notification handler that writes to `bot_outbound_messages` table (SQLite is shared across processes)
3. The agent-bot's `OutboundWorker` picks up the pending outbound message and delivers it via Telegram

**However**, this doesn't support file attachments via the outbound queue (text-only today).

**Better revised approach:** Add a `file_path` column to `bot_outbound_messages` and have OutboundWorker call `send_document` when present.

Let me restructure this task:

**Step 3 (revised): Extend outbound messages to support file attachments**

This task becomes two parts:

**Part A: Add `file_path` column to `bot_outbound_messages`**

Create migration `packages/core/src/flux_core/sqlite/migrations/005_outbound_file_path.sql`:
```sql
ALTER TABLE bot_outbound_messages ADD COLUMN file_path TEXT;
```

Update `packages/agent-bot/src/flux_bot/db/outbound.py` to include `file_path` in insert and fetch.

Update `packages/core/src/flux_core/use_cases/bot/send_message.py` to accept optional `file_path`.

**Part B: Update OutboundWorker to call `send_document` when file_path is present**

In `packages/agent-bot/src/flux_bot/orchestrator/outbound.py`, modify `_deliver_once`:
```python
if msg.get("file_path"):
    await channel.send_document(platform_id, msg["file_path"], msg["text"])
else:
    await channel.send_outbound(platform_id, msg["text"], msg.get("sender"))
```

**Part C: MCP server subscribes BackupNotificationHandler that writes outbound messages**

In the MCP server process, after backup completes, the handler creates an outbound message with `file_path` set for local backups.

This is a significantly different wiring than originally planned. Let me restructure tasks 6 and beyond.

---

**REVISED TASKS 6-9: Cross-process notification via outbound queue**

---

### Task 6: Add `file_path` Column to Outbound Messages

**Files:**
- Create: `packages/core/src/flux_core/sqlite/migrations/005_outbound_file_path.sql`
- Modify: `packages/agent-bot/src/flux_bot/db/outbound.py`
- Test: `packages/agent-bot/tests/test_orchestrator/test_outbound.py`

**Step 1: Write the failing test**

Check existing outbound repo to understand the insert/fetch interface.

In `packages/agent-bot/tests/test_orchestrator/test_outbound.py`, add:

```python
async def test_outbound_message_with_file_path(tmp_path):
    """Outbound messages with file_path are fetched correctly."""
    from flux_bot.db.outbound import OutboundRepository
    from flux_core.sqlite.database import Database
    from flux_core.sqlite.migrations.migrate import migrate

    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    db.connect()
    migrate(db)
    # Also run bot migrations
    from flux_bot.db.migrate import run_migrations
    await run_migrations(db_path)

    repo = OutboundRepository(db)
    await repo.insert(
        user_id="tg:12345",
        text="Backup completed",
        file_path="/data/backups/test.zip",
    )

    messages = await repo.fetch_pending()
    assert len(messages) == 1
    assert messages[0]["file_path"] == "/data/backups/test.zip"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_outbound.py::test_outbound_message_with_file_path -v`
Expected: FAIL (insert doesn't accept file_path yet)

**Step 3: Write minimal implementation**

Create migration `packages/core/src/flux_core/sqlite/migrations/005_outbound_file_path.sql`:
```sql
-- Add file_path support to outbound messages for backup attachments
ALTER TABLE bot_outbound_messages ADD COLUMN file_path TEXT;
```

Update `packages/agent-bot/src/flux_bot/db/outbound.py`:
- Add `file_path: str | None = None` param to `insert()`
- Include `file_path` in INSERT SQL
- Include `file_path` in SELECT in `fetch_pending()`

**Step 4: Run test to verify it passes**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_outbound.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/sqlite/migrations/005_outbound_file_path.sql packages/agent-bot/src/flux_bot/db/outbound.py packages/agent-bot/tests/test_orchestrator/test_outbound.py
git commit -m "feat: add file_path column to bot_outbound_messages"
```

---

### Task 7: OutboundWorker Calls `send_document` When `file_path` Present

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/orchestrator/outbound.py:67-89`
- Test: `packages/agent-bot/tests/test_orchestrator/test_outbound.py`

**Step 1: Write the failing test**

In `packages/agent-bot/tests/test_orchestrator/test_outbound.py`, add:

```python
async def test_deliver_with_file_path_calls_send_document():
    """OutboundWorker calls send_document when message has file_path."""
    from flux_bot.orchestrator.outbound import OutboundWorker

    outbound_repo = AsyncMock()
    outbound_repo.fetch_pending.return_value = [
        {
            "id": 1,
            "user_id": "tg:12345",
            "text": "Backup completed\n**File**: test.zip",
            "sender": None,
            "file_path": "/data/backups/test.zip",
        },
    ]
    outbound_repo.mark_sent = AsyncMock()

    channel = AsyncMock()
    channels = {"telegram": channel}

    worker = OutboundWorker(outbound_repo=outbound_repo, channels=channels)
    await worker._deliver_once()

    channel.send_document.assert_called_once_with(
        "12345", "/data/backups/test.zip",
        "Backup completed\n**File**: test.zip",
    )
    channel.send_outbound.assert_not_called()
    outbound_repo.mark_sent.assert_called_once_with(1)


async def test_deliver_without_file_path_calls_send_outbound():
    """OutboundWorker calls send_outbound for normal text messages."""
    from flux_bot.orchestrator.outbound import OutboundWorker

    outbound_repo = AsyncMock()
    outbound_repo.fetch_pending.return_value = [
        {
            "id": 2,
            "user_id": "tg:12345",
            "text": "Hello!",
            "sender": None,
            "file_path": None,
        },
    ]
    outbound_repo.mark_sent = AsyncMock()

    channel = AsyncMock()
    channels = {"telegram": channel}

    worker = OutboundWorker(outbound_repo=outbound_repo, channels=channels)
    await worker._deliver_once()

    channel.send_outbound.assert_called_once_with("12345", "Hello!", None)
    channel.send_document.assert_not_called()
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_outbound.py::test_deliver_with_file_path_calls_send_document -v`
Expected: FAIL (send_document not called, send_outbound called instead)

**Step 3: Write minimal implementation**

In `packages/agent-bot/src/flux_bot/orchestrator/outbound.py`, modify `_deliver_once`, replace the try block:

```python
            try:
                if msg.get("file_path"):
                    await channel.send_document(
                        platform_id, msg["file_path"], msg["text"]
                    )
                else:
                    await channel.send_outbound(platform_id, msg["text"], msg.get("sender"))
                await self.outbound_repo.mark_sent(msg["id"])
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/agent-bot && python -m pytest tests/test_orchestrator/test_outbound.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/agent-bot/src/flux_bot/orchestrator/outbound.py packages/agent-bot/tests/test_orchestrator/test_outbound.py
git commit -m "feat: OutboundWorker supports file attachments via send_document"
```

---

### Task 8: BackupNotificationHandler Writes Outbound Messages (MCP Server)

**Files:**
- Modify: `packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py` (revise to write outbound messages instead of sending directly)
- Create: `packages/core/src/flux_core/use_cases/bot/send_backup_notification.py`
- Test: `packages/core/tests/test_use_cases/test_backup_notification.py`

**Step 1: Write the failing test**

The notification handler now runs in the MCP server process and writes to `bot_outbound_messages`. Create a use case for this.

Create `packages/core/tests/test_use_cases/test_backup_notification.py`:

```python
"""Tests for SendBackupNotification use case."""
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from flux_core.events.events import BackupCompleted
from flux_core.use_cases.bot.send_backup_notification import SendBackupNotification


def _make_event(storage="local", size_bytes=4_200_000, local_path=None):
    return BackupCompleted(
        timestamp=datetime.now(UTC),
        filename="flux-backup-2026-03-14T020000.zip",
        size_bytes=size_bytes,
        storage=storage,
        user_id="tg:12345",
        local_path=local_path or (
            "/data/backups/flux-backup-2026-03-14T020000.zip" if storage == "local" else None
        ),
    )


async def test_local_small_backup_creates_outbound_with_file():
    """Local backup < 50MB creates outbound with file_path."""
    outbound_repo = AsyncMock()
    uc = SendBackupNotification(outbound_repo=outbound_repo, s3_configured_fn=lambda: False)

    event = _make_event(storage="local", size_bytes=4_200_000, local_path="/data/backups/test.zip")

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=4_200_000)
        await uc.execute(event)

    outbound_repo.insert.assert_called_once()
    kwargs = outbound_repo.insert.call_args[1]
    assert kwargs["user_id"] == "tg:12345"
    assert kwargs["file_path"] == "/data/backups/test.zip"
    assert "Backup completed" in kwargs["text"]
    assert "S3" in kwargs["text"]  # S3 tip


async def test_local_large_backup_creates_outbound_without_file():
    """Local backup >= 50MB creates text-only outbound."""
    outbound_repo = AsyncMock()
    uc = SendBackupNotification(outbound_repo=outbound_repo, s3_configured_fn=lambda: False)

    event = _make_event(storage="local", size_bytes=62_000_000, local_path="/data/backups/test.zip")

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=62_000_000)
        await uc.execute(event)

    outbound_repo.insert.assert_called_once()
    kwargs = outbound_repo.insert.call_args[1]
    assert kwargs.get("file_path") is None
    assert "too large" in kwargs["text"].lower()


async def test_s3_backup_creates_text_only_outbound():
    """S3 backup creates text-only outbound."""
    outbound_repo = AsyncMock()
    uc = SendBackupNotification(outbound_repo=outbound_repo, s3_configured_fn=lambda: True)

    event = _make_event(storage="s3")

    await uc.execute(event)

    outbound_repo.insert.assert_called_once()
    kwargs = outbound_repo.insert.call_args[1]
    assert kwargs.get("file_path") is None
    assert "s3" in kwargs["text"].lower()


async def test_local_no_s3_tip_when_configured():
    """No S3 tip in local backup notification when S3 is configured."""
    outbound_repo = AsyncMock()
    uc = SendBackupNotification(outbound_repo=outbound_repo, s3_configured_fn=lambda: True)

    event = _make_event(storage="local", size_bytes=4_200_000, local_path="/data/backups/test.zip")

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = MagicMock(st_size=4_200_000)
        await uc.execute(event)

    kwargs = outbound_repo.insert.call_args[1]
    assert "S3" not in kwargs["text"]
```

**Step 2: Run test to verify it fails**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup_notification.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `packages/core/src/flux_core/use_cases/bot/send_backup_notification.py`:

```python
"""SendBackupNotification — creates outbound message when backup completes."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import structlog

from flux_core.events.events import BackupCompleted

if TYPE_CHECKING:
    from flux_core.repositories.bot.outbound_repo import OutboundRepository

logger = structlog.get_logger(__name__)

_MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024  # 50MB


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024 or unit == "GB":
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


class SendBackupNotification:
    def __init__(
        self,
        outbound_repo: OutboundRepository,
        s3_configured_fn: Callable[[], bool],
    ):
        self._outbound_repo = outbound_repo
        self._s3_configured = s3_configured_fn

    async def execute(self, event: BackupCompleted) -> None:
        """Create an outbound message for the backup notification."""
        size_str = _format_size(event.size_bytes)
        base_msg = (
            f"Backup completed\n"
            f"**File**: {event.filename}\n"
            f"**Size**: {size_str}\n"
            f"**Storage**: {event.storage}"
        )

        s3_tip = ""
        if event.storage == "local" and not self._s3_configured():
            s3_tip = "\n\nTip: You can configure S3 backup in the web UI for cloud storage."

        file_path = None

        if event.storage == "local" and event.local_path:
            path = Path(event.local_path)
            if path.exists() and path.stat().st_size < _MAX_ATTACHMENT_SIZE:
                file_path = event.local_path
                text = base_msg + s3_tip
            else:
                text = base_msg + "\n\nFile too large to attach. Download from the web UI." + s3_tip
        else:
            text = base_msg

        await self._outbound_repo.insert(
            user_id=event.user_id,
            text=text,
            file_path=file_path,
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && python -m pytest tests/test_use_cases/test_backup_notification.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/use_cases/bot/send_backup_notification.py packages/core/tests/test_use_cases/test_backup_notification.py
git commit -m "feat: add SendBackupNotification use case"
```

---

### Task 9: Wire EventBus Subscriber in MCP Server

**Files:**
- Modify: `packages/mcp-server/src/flux_mcp/tools/backup_tools.py` (register subscriber)
- Modify: `packages/mcp-server/src/flux_mcp/server.py`
- Test: `packages/mcp-server/tests/test_backup_tools.py`

**Step 1: Write the failing test**

In `packages/mcp-server/tests/test_backup_tools.py`, add:

```python
async def test_create_backup_emits_event_and_notification_is_queued():
    """End-to-end: create_backup emits event → subscriber creates outbound message."""
    from flux_core.events.bus import EventBus
    from flux_core.events.events import BackupCompleted

    meta = BackupMetadata(
        id="2026-03-14T120000",
        filename="flux-backup-2026-03-14T120000.zip",
        size_bytes=1024,
        created_at=datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC),
        storage="local",
        local_path="/data/backups/flux-backup-2026-03-14T120000.zip",
    )

    mock_db = MagicMock()
    mock_local_storage = MagicMock()
    bus = EventBus()
    received_events = []

    async def capture(event):
        received_events.append(event)

    bus.subscribe(BackupCompleted, capture)

    with patch("flux_mcp.tools.backup_tools.CreateBackup") as MockCreateBackup:
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = meta
        MockCreateBackup.return_value = mock_uc

        from flux_mcp.tools.backup_tools import _create_backup_impl

        await _create_backup_impl(
            db=mock_db,
            zvec_path="/data/zvec",
            local_storage=mock_local_storage,
            s3_storage=None,
            storage="local",
            event_bus=bus,
            user_id="tg:12345",
        )

    MockCreateBackup.assert_called_once_with(
        mock_db, "/data/zvec", mock_local_storage, None,
        event_bus=bus, user_id="tg:12345",
    )
```

**Step 2: Run test — this should already pass**

Since we already wired event_bus through in Task 5, and CreateBackup emits events in Task 2, the MCP integration is already complete. The subscriber registration happens at the use case level (CreateBackup emits), not at the MCP server level.

Run: `cd packages/mcp-server && python -m pytest tests/test_backup_tools.py -v`
Expected: ALL PASS

**Step 3: Register the notification subscriber on the MCP server's EventBus**

The `SendBackupNotification` use case needs to be subscribed to `BackupCompleted` on the shared EventBus in the MCP server process.

In `packages/mcp-server/src/flux_mcp/server.py`, after `register_backup_tools(...)`:

```python
# Subscribe backup notification handler
from flux_core.events.events import BackupCompleted
from flux_core.use_cases.bot.send_backup_notification import SendBackupNotification
from flux_core.sqlite.bot.outbound_repo import SqliteOutboundRepository

def _setup_backup_notifications():
    bus = get_event_bus()
    outbound_repo = SqliteOutboundRepository(get_db().connection())
    notifier = SendBackupNotification(
        outbound_repo=outbound_repo,
        s3_configured_fn=lambda: get_s3_storage() is not None,
    )
    bus.subscribe(BackupCompleted, notifier.execute)

_setup_backup_notifications()
```

**Note:** Check if `SqliteOutboundRepository` exists in core or only in agent-bot. If it's only in agent-bot, we need to either:
- Move it to core, or
- Create a minimal outbound insert function in core

This needs investigation during implementation. The outbound repo protocol is in `packages/core/src/flux_core/repositories/bot/outbound_repo.py` but the SQLite implementation may be in agent-bot at `packages/agent-bot/src/flux_bot/db/outbound.py`. If so, we need to add a simple insert-only implementation to core.

**Step 4: Run all tests**

Run: `cd packages/mcp-server && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add packages/mcp-server/src/flux_mcp/server.py packages/mcp-server/tests/test_backup_tools.py
git commit -m "feat: wire backup notification subscriber in MCP server"
```

---

### Task 10: Clean Up — Remove Standalone `backup_notify.py` from Agent Bot

**Files:**
- Delete: `packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py` (if created in Task 4)
- Delete: `packages/agent-bot/tests/test_orchestrator/test_backup_notify.py` (if created in Task 4)

Since we moved the notification logic to `packages/core` (SendBackupNotification use case) and the wiring to the MCP server, the agent-bot `backup_notify.py` module from Task 4 is no longer needed.

**Note:** If Task 4 was not yet implemented when this plan is executed, skip Task 4 entirely and go straight to Task 8.

**Step 1: Remove files**

```bash
rm packages/agent-bot/src/flux_bot/orchestrator/backup_notify.py
rm packages/agent-bot/tests/test_orchestrator/test_backup_notify.py
```

**Step 2: Run all tests to ensure nothing breaks**

```bash
cd packages/agent-bot && python -m pytest tests/ -v
cd packages/core && python -m pytest tests/ -v
cd packages/mcp-server && python -m pytest tests/ -v
```

**Step 3: Commit**

```bash
git add -u
git commit -m "chore: remove unused backup_notify from agent-bot"
```

---

### Task 11: Full Integration Test

**Files:**
- Run all test suites to verify nothing is broken

**Step 1: Run all tests**

```bash
./test-all.sh
```

Expected: ALL PASS across all packages.

**Step 2: Verify coverage**

```bash
./test-all.sh --coverage
```

Expected: >= 90% coverage across all packages.

---

## Task Summary

| Task | Description | Package |
|------|-------------|---------|
| 1 | Add `BackupCompleted` event | core |
| 2 | `CreateBackup` emits events | core |
| 3 | Add `send_document()` to TelegramChannel | agent-bot |
| 4 | ~~BackupNotificationHandler in agent-bot~~ **SKIP** — replaced by Tasks 8-9 | — |
| 5 | MCP tools pass `event_bus` + `user_id` | mcp-server |
| 6 | Add `file_path` column to outbound messages | core + agent-bot |
| 7 | OutboundWorker calls `send_document` for file messages | agent-bot |
| 8 | `SendBackupNotification` use case | core |
| 9 | Wire subscriber in MCP server | mcp-server |
| 10 | Clean up unused files | agent-bot |
| 11 | Full integration test | all |

**Key insight:** MCP server runs as a separate subprocess, so EventBus cannot span processes. Notifications are written to `bot_outbound_messages` (shared SQLite) and delivered by the agent-bot's OutboundWorker.
