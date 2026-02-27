"""Unit tests for slash command handlers."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from flux_bot.channels.commands import CommandHandlers, HELP_TEXT, _MENU, _EDIT_CURRENCY, _EDIT_TIMEZONE, _EDIT_USERNAME  # noqa: E501
from flux_core.models.user_profile import UserProfile


def _make_handlers(profile=None):
    profile_repo = AsyncMock()
    profile_repo.get_by_platform_id.return_value = profile
    profile_repo.get_by_user_id.return_value = profile
    profile_repo.update = AsyncMock(return_value=profile)

    session_repo = AsyncMock()
    session_repo.delete = AsyncMock()

    task_repo = AsyncMock()
    task_repo.list_by_user = AsyncMock(return_value=[])

    handlers = CommandHandlers(
        profile_repo=profile_repo,
        session_repo=session_repo,
        task_repo=task_repo,
    )
    # Expose mocks for assertion in tests
    handlers.session_repo = session_repo
    handlers.task_repo = task_repo
    handlers.profile_repo = profile_repo
    return handlers


def _make_update(user_id=12345, text="/help"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


def _make_profile(user_id="tg:12345", username="alice"):
    return UserProfile(
        user_id=user_id,
        username=username,
        channel="telegram",
        platform_id="12345",
        currency="VND",
        timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def test_help_replies_with_help_text():
    handlers = _make_handlers()
    update = _make_update(text="/help")
    await handlers.cmd_help(update, MagicMock())
    update.message.reply_text.assert_called_once_with(HELP_TEXT, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /reset
# ---------------------------------------------------------------------------

async def test_reset_deletes_session_for_known_user():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="/reset")
    await handlers.cmd_reset(update, MagicMock())
    handlers.session_repo.delete.assert_called_once_with("tg:12345")
    update.message.reply_text.assert_called_once()
    assert "reset" in update.message.reply_text.call_args[0][0].lower()


async def test_reset_unknown_user_replies_without_deleting():
    handlers = _make_handlers(profile=None)
    update = _make_update(text="/reset")
    await handlers.cmd_reset(update, MagicMock())
    handlers.session_repo.delete.assert_not_called()
    update.message.reply_text.assert_called_once()
