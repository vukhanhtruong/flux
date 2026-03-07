"""Tests for /backup and /restore bot commands."""
from unittest.mock import AsyncMock, MagicMock, patch

from flux_core.models.user_profile import UserProfile


def _mock_update(user_id=12345):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    return update


def _mock_context():
    ctx = MagicMock()
    ctx.user_data = {}
    return ctx


def _mock_profile():
    return UserProfile(
        user_id="tg:12345",
        username="alice",
        channel="telegram",
        platform_id="12345",
        currency="VND",
        timezone="UTC",
        locale="vi-VN",
    )


def _make_handlers(profile=None):
    from flux_bot.channels.commands import CommandHandlers

    profile_repo = AsyncMock()
    profile_repo.get_by_platform_id.return_value = profile
    return CommandHandlers(
        profile_repo=profile_repo, session_repo=AsyncMock(), task_repo=AsyncMock()
    )


async def test_cmd_backup_no_profile():
    cmds = _make_handlers(profile=None)
    update = _mock_update()
    await cmds.cmd_backup(update, _mock_context())
    update.message.reply_text.assert_called_once()
    assert "setup" in update.message.reply_text.call_args[0][0].lower()


async def test_cmd_restore_no_profile():
    cmds = _make_handlers(profile=None)
    update = _mock_update()
    await cmds.cmd_restore(update, _mock_context())
    update.message.reply_text.assert_called_once()
    assert "setup" in update.message.reply_text.call_args[0][0].lower()


async def test_cmd_backup_with_s3(monkeypatch):
    cmds = _make_handlers(profile=_mock_profile())
    monkeypatch.setattr(cmds, "_get_s3_configured", lambda: True)
    update = _mock_update()
    await cmds.cmd_backup(update, _mock_context())
    # Should show inline keyboard with telegram/s3 options
    call_kwargs = update.message.reply_text.call_args
    assert call_kwargs.kwargs.get("reply_markup") is not None


async def test_cmd_backup_no_s3_sends_file(monkeypatch, tmp_path):
    """Without S3, backup creates a local file and sends it via Telegram."""
    cmds = _make_handlers(profile=_mock_profile())
    monkeypatch.setattr(cmds, "_get_s3_configured", lambda: False)

    # Create a fake zip file to be "sent"
    fake_zip = tmp_path / "flux-backup-2026-03-07.zip"
    fake_zip.write_bytes(b"PK fake zip content")

    mock_meta = MagicMock()
    mock_meta.filename = "flux-backup-2026-03-07.zip"
    mock_meta.size_bytes = 19

    mock_uc = AsyncMock()
    mock_uc.execute = AsyncMock(return_value=mock_meta)

    mock_local = MagicMock()
    mock_local._dir = str(tmp_path)

    mock_db = MagicMock()

    with (
        patch(
            "flux_core.use_cases.backup.create_backup.CreateBackup",
            return_value=mock_uc,
        ),
        patch("flux_core.sqlite.database.Database", return_value=mock_db),
        patch(
            "flux_core.services.storage.local.LocalStorageProvider",
            return_value=mock_local,
        ),
    ):
        update = _mock_update()
        await cmds.cmd_backup(update, _mock_context())

    # Should have sent the document
    update.message.reply_document.assert_called_once()
    call_kwargs = update.message.reply_document.call_args[1]
    assert call_kwargs["filename"] == "flux-backup-2026-03-07.zip"


async def test_cmd_backup_no_s3_handles_error(monkeypatch):
    """When backup fails, error message is sent to user."""
    cmds = _make_handlers(profile=_mock_profile())
    monkeypatch.setattr(cmds, "_get_s3_configured", lambda: False)

    with (
        patch(
            "flux_core.use_cases.backup.create_backup.CreateBackup",
            side_effect=Exception("disk full"),
        ),
        patch("flux_core.sqlite.database.Database", return_value=MagicMock()),
        patch("flux_core.services.storage.local.LocalStorageProvider"),
    ):
        update = _mock_update()
        await cmds.cmd_backup(update, _mock_context())

    # First call is "Creating backup..." and second is "Backup failed: ..."
    calls = update.message.reply_text.call_args_list
    assert any("failed" in str(c).lower() for c in calls)


async def test_cmd_restore_shows_instructions():
    cmds = _make_handlers(profile=_mock_profile())
    update = _mock_update()
    await cmds.cmd_restore(update, _mock_context())
    msg = update.message.reply_text.call_args[0][0]
    assert "zip" in msg.lower()


async def test_help_text_contains_backup_restore():
    from flux_bot.channels.commands import HELP_TEXT

    assert "/backup" in HELP_TEXT
    assert "/restore" in HELP_TEXT
