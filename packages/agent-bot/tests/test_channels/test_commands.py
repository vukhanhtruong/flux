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


# ---------------------------------------------------------------------------
# /tasks
# ---------------------------------------------------------------------------

async def test_tasks_no_tasks_sends_empty_message():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.task_repo.list_by_user.return_value = []
    update = _make_update(text="/tasks")
    await handlers.cmd_tasks(update, MagicMock())
    update.message.reply_text.assert_called_once()
    assert "no scheduled tasks" in update.message.reply_text.call_args[0][0].lower()


async def test_tasks_shows_task_list():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.task_repo.list_by_user.return_value = [
        {
            "id": 1,
            "prompt": "Weekly spending report",
            "schedule_type": "interval",
            "schedule_value": "604800000",
            "next_run_at": datetime.now(UTC) + timedelta(days=3),
        }
    ]
    update = _make_update(text="/tasks")
    await handlers.cmd_tasks(update, MagicMock())
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "Weekly spending report" in text
    assert "🔁" in text


async def test_tasks_unknown_user_replies_gracefully():
    handlers = _make_handlers(profile=None)
    update = _make_update(text="/tasks")
    await handlers.cmd_tasks(update, MagicMock())
    update.message.reply_text.assert_called_once()
    handlers.task_repo.list_by_user.assert_not_called()


async def test_tasks_long_prompt_is_truncated():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    long_prompt = "A" * 100
    handlers.task_repo.list_by_user.return_value = [
        {
            "id": 1,
            "prompt": long_prompt,
            "schedule_type": "once",
            "schedule_value": "2026-03-01T08:00:00",
            "next_run_at": datetime.now(UTC) + timedelta(days=1),
        }
    ]
    update = _make_update(text="/tasks")
    await handlers.cmd_tasks(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "…" in text
    assert long_prompt not in text


# ---------------------------------------------------------------------------
# /settings
# ---------------------------------------------------------------------------

async def test_settings_shows_menu_for_known_user():
    from telegram.ext import ConversationHandler
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="/settings")
    result = await handlers.cmd_settings(update, MagicMock())
    update.message.reply_text.assert_called_once()
    call_kwargs = update.message.reply_text.call_args[1]
    assert "reply_markup" in call_kwargs
    assert result != ConversationHandler.END


async def test_settings_unknown_user_ends_conversation():
    from telegram.ext import ConversationHandler
    handlers = _make_handlers(profile=None)
    update = _make_update(text="/settings")
    result = await handlers.cmd_settings(update, MagicMock())
    assert result == ConversationHandler.END


async def test_settings_currency_valid_input_updates_profile():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="USD")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_currency_input(update, context)
    handlers.profile_repo.update.assert_called_once_with("tg:12345", currency="USD")
    update.message.reply_text.assert_called()
    assert result == _MENU


async def test_settings_currency_invalid_input_stays_in_state():
    handlers = _make_handlers()
    update = _make_update(text="not-valid-123!!")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_currency_input(update, context)
    handlers.profile_repo.update.assert_not_called()
    assert result == _EDIT_CURRENCY


async def test_settings_timezone_valid_updates_profile():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="UTC")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_timezone_input(update, context)
    handlers.profile_repo.update.assert_called_once_with("tg:12345", timezone="UTC")
    assert result == _MENU


async def test_settings_timezone_invalid_stays_in_state():
    handlers = _make_handlers()
    update = _make_update(text="Not/A/Real/Zone")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_timezone_input(update, context)
    handlers.profile_repo.update.assert_not_called()
    assert result == _EDIT_TIMEZONE


async def test_settings_username_valid_updates_profile():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="new-name")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_username_input(update, context)
    handlers.profile_repo.update.assert_called_once_with("tg:12345", username="new-name")
    assert result == _MENU


async def test_settings_username_too_short_stays_in_state():
    handlers = _make_handlers()
    update = _make_update(text="ab")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_username_input(update, context)
    handlers.profile_repo.update.assert_not_called()
    assert result == _EDIT_USERNAME


async def test_settings_username_taken_stays_in_state():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.profile_repo.update.side_effect = ValueError("username already taken")
    update = _make_update(text="taken-name")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_username_input(update, context)
    assert result == _EDIT_USERNAME
    assert "taken" in update.message.reply_text.call_args[0][0].lower()


async def test_settings_menu_done_ends_conversation():
    from telegram.ext import ConversationHandler
    handlers = _make_handlers()
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "done"
    result = await handlers._settings_menu_callback(update, MagicMock())
    assert result == ConversationHandler.END


async def test_settings_menu_currency_advances_to_edit_state():
    handlers = _make_handlers()
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "currency"
    result = await handlers._settings_menu_callback(update, MagicMock())
    assert result == _EDIT_CURRENCY


async def test_settings_menu_timezone_advances_to_edit_state():
    handlers = _make_handlers()
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "timezone"
    result = await handlers._settings_menu_callback(update, MagicMock())
    assert result == _EDIT_TIMEZONE


async def test_settings_menu_username_advances_to_edit_state():
    handlers = _make_handlers()
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "username"
    result = await handlers._settings_menu_callback(update, MagicMock())
    assert result == _EDIT_USERNAME


async def test_settings_conversation_handler_is_configured():
    from telegram.ext import ConversationHandler
    handlers = _make_handlers()
    conv = handlers.settings_conversation()
    assert isinstance(conv, ConversationHandler)
