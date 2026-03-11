"""Unit tests for slash command handlers."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from flux_bot.channels.commands import (  # noqa: E501
    CommandHandlers,
    HELP_TEXT,
    _MENU,
    _EDIT_CURRENCY,
    _EDIT_TIMEZONE,
    _EDIT_USERNAME,
    _OB_CURRENCY,
    _OB_TIMEZONE,
    _OB_USERNAME,
    _OB_BACKUP,
    _OB_BACKUP_CONFIRM,
    _validate_currency,
    _validate_timezone,
    _lookup_timezone_for_location,
)
from flux_core.models.user_profile import UserProfile


# ---------------------------------------------------------------------------
# Pure validator helpers
# ---------------------------------------------------------------------------

def test_validate_currency_valid():
    assert _validate_currency("usd") == "USD"
    assert _validate_currency(" EUR ") == "EUR"
    assert _validate_currency("VND") == "VND"


def test_validate_currency_invalid():
    assert _validate_currency("not-valid!!") is None
    assert _validate_currency("TOOLONG") is None
    assert _validate_currency("1BC") is None


def test_validate_timezone_valid():
    assert _validate_timezone("UTC") == "UTC"
    assert _validate_timezone(" Asia/Ho_Chi_Minh ") == "Asia/Ho_Chi_Minh"


def test_validate_timezone_invalid():
    assert _validate_timezone("Not/A/Real/Zone") is None


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_handlers(profile=None):
    profile_repo = AsyncMock()
    profile_repo.get_by_platform_id.return_value = profile
    profile_repo.get_by_user_id.return_value = profile
    profile_repo.update = AsyncMock(return_value=profile)
    profile_repo.create = AsyncMock()

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
    update = _make_update(text="My Display Name!")
    context = MagicMock()
    context.user_data = {"user_id": "tg:12345"}
    result = await handlers._handle_username_input(update, context)
    handlers.profile_repo.update.assert_called_once_with("tg:12345", username="My Display Name!")
    assert result == _MENU


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


# ---------------------------------------------------------------------------
# /onboard
# ---------------------------------------------------------------------------

def _make_context(user_data=None):
    """Build a context mock with a real dict for user_data."""
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    return ctx


def _make_callback_update(user_id=12345, callback_data="ob_skip"):
    """Build an Update with a callback_query (simulates inline button tap)."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message = None
    cq = AsyncMock()
    cq.data = callback_data
    cq.answer = AsyncMock()
    cq.message = MagicMock()
    cq.message.reply_text = AsyncMock()
    update.callback_query = cq
    return update


async def test_onboard_new_user_starts_currency_prompt():
    """New user (no profile) → /onboard sends currency prompt without Skip button."""
    handlers = _make_handlers(profile=None)
    update = _make_update(text="/onboard")
    context = _make_context()
    result = await handlers.cmd_onboard(update, context)
    assert result == _OB_CURRENCY
    assert context.user_data["ob_is_new_user"] is True
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "Currency" in text
    # No Skip button — reply_markup should not be in kwargs
    kwargs = update.message.reply_text.call_args[1]
    assert "reply_markup" not in kwargs


async def test_onboard_sends_currency_prompt():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="/onboard")
    result = await handlers.cmd_onboard(update, MagicMock())
    assert result == _OB_CURRENCY
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "Currency" in text


async def test_ob_handle_currency_valid():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="USD")
    result = await handlers._ob_handle_currency(update, _make_context())
    handlers.profile_repo.update.assert_called_once_with("tg:12345", currency="USD")
    assert result == _OB_TIMEZONE
    # Should send the timezone prompt
    text = update.message.reply_text.call_args[0][0]
    assert "Timezone" in text


async def test_ob_handle_currency_invalid():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="not-valid!!")
    result = await handlers._ob_handle_currency(update, _make_context())
    handlers.profile_repo.update.assert_not_called()
    assert result == _OB_CURRENCY
    # First call is the error, second call is the re-sent prompt
    assert update.message.reply_text.call_count == 2
    error_text = update.message.reply_text.call_args_list[0][0][0]
    assert "❌" in error_text


async def test_ob_skip_currency():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_callback_update(callback_data="ob_skip")
    result = await handlers._ob_skip_currency(update, MagicMock())
    assert result == _OB_TIMEZONE
    update.callback_query.answer.assert_called_once()
    update.callback_query.message.reply_text.assert_called_once()
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "Timezone" in text


async def test_ob_handle_timezone_valid():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="UTC")
    result = await handlers._ob_handle_timezone(update, _make_context())
    handlers.profile_repo.update.assert_called_once_with("tg:12345", timezone="UTC")
    assert result == _OB_USERNAME
    text = update.message.reply_text.call_args[0][0]
    assert "Username" in text


async def test_ob_handle_timezone_invalid():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="Not/A/Real/Zone")
    result = await handlers._ob_handle_timezone(update, _make_context())
    handlers.profile_repo.update.assert_not_called()
    assert result == _OB_TIMEZONE
    assert update.message.reply_text.call_count == 2
    error_text = update.message.reply_text.call_args_list[0][0][0]
    assert "❌" in error_text


async def test_ob_skip_timezone():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_callback_update(callback_data="ob_skip")
    result = await handlers._ob_skip_timezone(update, MagicMock())
    assert result == _OB_USERNAME
    update.callback_query.answer.assert_called_once()
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "Username" in text


async def test_ob_handle_username_valid():
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="My Display Name 123!")
    result = await handlers._ob_handle_username(update, _make_context())
    handlers.profile_repo.update.assert_called_once_with("tg:12345", username="My Display Name 123!")
    assert result == _OB_BACKUP
    text = update.message.reply_text.call_args[0][0]
    assert "Auto-backup" in text


async def test_ob_skip_username():
    handlers = _make_handlers()
    update = _make_callback_update(callback_data="ob_skip")
    result = await handlers._ob_skip_username(update, MagicMock())
    assert result == _OB_BACKUP
    update.callback_query.answer.assert_called_once()
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "Auto-backup" in text


async def test_ob_new_user_handle_currency_stores_in_context():
    """New user valid currency is stored in user_data, DB not updated."""
    handlers = _make_handlers(profile=None)
    update = _make_update(text="USD")
    context = _make_context({"ob_is_new_user": True, "ob_platform_id": "12345"})
    result = await handlers._ob_handle_currency(update, context)
    assert result == _OB_TIMEZONE
    assert context.user_data["ob_currency"] == "USD"
    handlers.profile_repo.update.assert_not_called()
    # Prompt sent without Skip button
    text = update.message.reply_text.call_args[0][0]
    assert "Timezone" in text
    kwargs = update.message.reply_text.call_args[1]
    assert "reply_markup" not in kwargs


async def test_ob_new_user_handle_timezone_stores_in_context():
    """New user valid timezone is stored in user_data, DB not updated."""
    handlers = _make_handlers(profile=None)
    update = _make_update(text="UTC")
    context = _make_context({"ob_is_new_user": True, "ob_platform_id": "12345"})
    result = await handlers._ob_handle_timezone(update, context)
    assert result == _OB_USERNAME
    assert context.user_data["ob_timezone"] == "UTC"
    handlers.profile_repo.update.assert_not_called()
    text = update.message.reply_text.call_args[0][0]
    assert "Username" in text
    kwargs = update.message.reply_text.call_args[1]
    assert "reply_markup" not in kwargs


async def test_ob_new_user_completes_creates_profile():
    """New user completing username step calls profile_repo.create, advances to backup."""
    from flux_core.models.user_profile import UserProfileCreate

    handlers = _make_handlers(profile=None)
    update = _make_update(text="alice-new")
    context = _make_context({
        "ob_is_new_user": True,
        "ob_platform_id": "99999",
        "ob_currency": "USD",
        "ob_timezone": "UTC",
    })
    result = await handlers._ob_handle_username(update, context)
    assert result == _OB_BACKUP
    handlers.profile_repo.create.assert_called_once()
    call_arg = handlers.profile_repo.create.call_args[0][0]
    assert isinstance(call_arg, UserProfileCreate)
    assert call_arg.username == "alice-new"
    assert call_arg.platform_id == "99999"
    assert call_arg.currency == "USD"
    assert call_arg.timezone == "UTC"
    assert call_arg.channel == "telegram"
    handlers.profile_repo.update.assert_not_called()
    text = update.message.reply_text.call_args[0][0]
    assert "Auto-backup" in text


async def test_onboard_conversation_has_correct_structure():
    from telegram.ext import ConversationHandler
    handlers = _make_handlers()
    conv = handlers.onboard_conversation()
    assert isinstance(conv, ConversationHandler)
    assert _OB_CURRENCY in conv.states
    assert _OB_TIMEZONE in conv.states
    assert _OB_USERNAME in conv.states
    assert _OB_BACKUP in conv.states
    assert conv.conversation_timeout == 600


# ---------------------------------------------------------------------------
# _lookup_timezone_for_location — pure function tests
# ---------------------------------------------------------------------------

def test_lookup_timezone_for_location_alias():
    """Abbreviation 'ict' → list containing Asia/Ho_Chi_Minh."""
    results = _lookup_timezone_for_location("ict")
    assert "Asia/Ho_Chi_Minh" in results


def test_lookup_timezone_for_location_country():
    """Country name 'vietnam' → exactly ['Asia/Ho_Chi_Minh']."""
    results = _lookup_timezone_for_location("vietnam")
    assert results == ["Asia/Ho_Chi_Minh"]


def test_lookup_timezone_for_location_utc_offset():
    """UTC offset string 'gmt+7' → list containing Asia/Ho_Chi_Minh."""
    results = _lookup_timezone_for_location("gmt+7")
    assert "Asia/Ho_Chi_Minh" in results


def test_lookup_timezone_for_location_substring():
    """Substring fallback: 'Ho_Chi' (mixed case) → contains Asia/Ho_Chi_Minh."""
    results = _lookup_timezone_for_location("Ho_Chi")
    assert "Asia/Ho_Chi_Minh" in results


def test_lookup_timezone_for_location_no_match():
    """Completely unknown string → empty list."""
    results = _lookup_timezone_for_location("nonsense123xyz")
    assert results == []


# ---------------------------------------------------------------------------
# /onboard location-based timezone handler tests
# ---------------------------------------------------------------------------

async def test_ob_handle_timezone_location_single_result():
    """Typing 'vietnam' (single candidate) → sends ob_tz: button, stays in _OB_TIMEZONE."""
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="vietnam")
    context = _make_context()
    result = await handlers._ob_handle_timezone(update, context)
    assert result == _OB_TIMEZONE
    handlers.profile_repo.update.assert_not_called()
    update.message.reply_text.assert_called_once()
    call_kwargs = update.message.reply_text.call_args[1]
    assert "reply_markup" in call_kwargs
    markup = call_kwargs["reply_markup"]
    # Check that at least one button has callback_data starting with "ob_tz:"
    all_buttons = [btn for row in markup.inline_keyboard for btn in row]
    assert any(btn.callback_data.startswith("ob_tz:") for btn in all_buttons)


async def test_ob_handle_timezone_location_multi_result():
    """Typing 'ict' (multiple candidates) → sends multiple ob_tz: buttons, stays in _OB_TIMEZONE."""
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="ict")
    context = _make_context()
    result = await handlers._ob_handle_timezone(update, context)
    assert result == _OB_TIMEZONE
    handlers.profile_repo.update.assert_not_called()
    update.message.reply_text.assert_called_once()
    call_kwargs = update.message.reply_text.call_args[1]
    assert "reply_markup" in call_kwargs
    markup = call_kwargs["reply_markup"]
    tz_buttons = [
        btn for row in markup.inline_keyboard for btn in row
        if btn.callback_data.startswith("ob_tz:")
    ]
    assert len(tz_buttons) > 1


async def test_ob_handle_timezone_location_no_match():
    """Typing 'nonsense123xyz' → error reply + re-prompt, stays in _OB_TIMEZONE."""
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_update(text="nonsense123xyz")
    context = _make_context()
    result = await handlers._ob_handle_timezone(update, context)
    assert result == _OB_TIMEZONE
    handlers.profile_repo.update.assert_not_called()
    assert update.message.reply_text.call_count == 2
    error_text = update.message.reply_text.call_args_list[0][0][0]
    assert "❌" in error_text


# ---------------------------------------------------------------------------
# /settings _settings_timezone_button handler
# ---------------------------------------------------------------------------

async def test_settings_timezone_button():
    """Callback 'settings_tz:UTC' → updates profile timezone to UTC, returns _MENU."""
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "settings_tz:UTC"
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = MagicMock()
    update.callback_query.message.reply_text = AsyncMock()
    context = _make_context({"user_id": "tg:12345"})
    result = await handlers._settings_timezone_button(update, context)
    handlers.profile_repo.update.assert_called_once_with("tg:12345", timezone="UTC")
    assert result == _MENU


async def test_ob_tz_button_new_user_stores_in_context():
    """Tapping ob_tz: button as new user → stores tz in user_data, advances to _OB_USERNAME."""
    handlers = _make_handlers(profile=None)
    update = _make_callback_update(callback_data="ob_tz:Asia/Ho_Chi_Minh")
    context = _make_context({"ob_is_new_user": True, "ob_platform_id": "12345"})
    result = await handlers._ob_tz_button(update, context)
    assert context.user_data["ob_timezone"] == "Asia/Ho_Chi_Minh"
    handlers.profile_repo.update.assert_not_called()
    assert result == _OB_USERNAME
    update.callback_query.message.reply_text.assert_called_once()
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "Username" in text


async def test_ob_tz_button_existing_user_updates_profile():
    """Tapping ob_tz: button as existing user → updates DB, advances to _OB_USERNAME."""
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    update = _make_callback_update(callback_data="ob_tz:Asia/Tokyo")
    context = _make_context({"ob_is_new_user": False})
    result = await handlers._ob_tz_button(update, context)
    handlers.profile_repo.update.assert_called_once_with("tg:12345", timezone="Asia/Tokyo")
    assert result == _OB_USERNAME


async def test_onboard_conversation_handles_ob_tz_callbacks():
    """_OB_TIMEZONE state must include a CallbackQueryHandler for ob_tz: pattern."""
    from telegram.ext import CallbackQueryHandler as CQH
    handlers = _make_handlers()
    conv = handlers.onboard_conversation()
    tz_state_handlers = conv.states[_OB_TIMEZONE]
    patterns = [
        h.pattern.pattern
        for h in tz_state_handlers
        if isinstance(h, CQH) and h.pattern is not None
    ]
    assert any("ob_tz" in p for p in patterns), (
        f"No ob_tz: CallbackQueryHandler found in _OB_TIMEZONE state. Got patterns: {patterns}"
    )


# ---------------------------------------------------------------------------
# /onboard — backup preference step (4/4)
# ---------------------------------------------------------------------------

async def test_ob_handle_backup_daily_creates_scheduled_task():
    from telegram.ext import ConversationHandler
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.task_repo.create = AsyncMock(return_value=1)
    handlers.task_repo.list_by_user = AsyncMock(return_value=[])  # no existing backup
    update = _make_callback_update(callback_data="ob_backup:daily")
    result = await handlers._ob_handle_backup(update, _make_context())
    assert result == ConversationHandler.END
    update.callback_query.answer.assert_called_once()
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "daily" in text.lower()
    assert HELP_TEXT in text
    # Must actually create a scheduled task
    handlers.task_repo.create.assert_called_once()
    call_kwargs = handlers.task_repo.create.call_args
    assert call_kwargs[1]["user_id"] == "tg:12345"
    assert call_kwargs[1]["schedule_type"] == "cron"
    assert call_kwargs[1]["schedule_value"] == "0 2 * * *"
    assert "backup" in call_kwargs[1]["prompt"].lower()


async def test_ob_handle_backup_weekly_creates_scheduled_task():
    from telegram.ext import ConversationHandler
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.task_repo.create = AsyncMock(return_value=2)
    handlers.task_repo.list_by_user = AsyncMock(return_value=[])  # no existing backup
    update = _make_callback_update(callback_data="ob_backup:weekly")
    result = await handlers._ob_handle_backup(update, _make_context())
    assert result == ConversationHandler.END
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "weekly" in text.lower()
    # Must actually create a scheduled task
    handlers.task_repo.create.assert_called_once()
    call_kwargs = handlers.task_repo.create.call_args
    assert call_kwargs[1]["user_id"] == "tg:12345"
    assert call_kwargs[1]["schedule_type"] == "cron"
    assert call_kwargs[1]["schedule_value"] == "0 2 * * 0"
    assert "backup" in call_kwargs[1]["prompt"].lower()


async def test_ob_handle_backup_never_does_not_create_task():
    from telegram.ext import ConversationHandler
    handlers = _make_handlers()
    handlers.task_repo.create = AsyncMock()
    update = _make_callback_update(callback_data="ob_backup:never")
    result = await handlers._ob_handle_backup(update, _make_context())
    assert result == ConversationHandler.END
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "No auto-backup" in text
    # Must NOT create a scheduled task
    handlers.task_repo.create.assert_not_called()


async def test_ob_handle_backup_daily_existing_asks_confirm():
    """Selecting daily when a backup task exists → asks user to replace or keep."""
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.task_repo.create = AsyncMock(return_value=1)
    handlers.task_repo.list_by_user = AsyncMock(return_value=[
        {"id": 99, "prompt": "Create a backup of my data", "schedule_type": "cron",
         "schedule_value": "0 2 * * 0", "next_run_at": None, "status": "active"},
    ])
    update = _make_callback_update(callback_data="ob_backup:daily")
    context = _make_context()
    from flux_bot.channels.commands import _OB_BACKUP_CONFIRM
    result = await handlers._ob_handle_backup(update, context)
    assert result == _OB_BACKUP_CONFIRM
    # Should NOT create a task yet
    handlers.task_repo.create.assert_not_called()
    # Should show replace/keep buttons
    call_kwargs = update.callback_query.message.reply_text.call_args[1]
    assert "reply_markup" in call_kwargs
    # Choice stored in context for the confirm handler
    assert context.user_data["ob_backup_choice"] == "daily"
    assert context.user_data["ob_backup_existing_id"] == 99


async def test_ob_handle_backup_confirm_replace_deletes_old_creates_new():
    """User picks 'Replace' → old task deleted, new one created."""
    from telegram.ext import ConversationHandler
    profile = _make_profile()
    handlers = _make_handlers(profile=profile)
    handlers.task_repo.create = AsyncMock(return_value=2)
    handlers.task_repo.delete = AsyncMock()
    update = _make_callback_update(callback_data="ob_backup_confirm:replace")
    context = _make_context({
        "ob_backup_choice": "daily",
        "ob_backup_existing_id": 99,
    })
    result = await handlers._ob_handle_backup_confirm(update, context)
    assert result == ConversationHandler.END
    handlers.task_repo.delete.assert_called_once_with(99)
    handlers.task_repo.create.assert_called_once()
    call_kwargs = handlers.task_repo.create.call_args[1]
    assert call_kwargs["schedule_value"] == "0 2 * * *"
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "daily" in text.lower()
    assert HELP_TEXT in text


async def test_ob_handle_backup_confirm_keep_skips_creation():
    """User picks 'Keep existing' → no delete, no create."""
    from telegram.ext import ConversationHandler
    handlers = _make_handlers()
    handlers.task_repo.create = AsyncMock()
    handlers.task_repo.delete = AsyncMock()
    update = _make_callback_update(callback_data="ob_backup_confirm:keep")
    context = _make_context({
        "ob_backup_choice": "weekly",
        "ob_backup_existing_id": 99,
    })
    result = await handlers._ob_handle_backup_confirm(update, context)
    assert result == ConversationHandler.END
    handlers.task_repo.delete.assert_not_called()
    handlers.task_repo.create.assert_not_called()
    text = update.callback_query.message.reply_text.call_args[0][0]
    assert "keep" in text.lower() or "existing" in text.lower()
    assert HELP_TEXT in text


async def test_onboard_conversation_handles_ob_backup_callbacks():
    """_OB_BACKUP state must include a CallbackQueryHandler for ob_backup: pattern."""
    from telegram.ext import CallbackQueryHandler as CQH
    handlers = _make_handlers()
    conv = handlers.onboard_conversation()
    backup_state_handlers = conv.states[_OB_BACKUP]
    patterns = [
        h.pattern.pattern
        for h in backup_state_handlers
        if isinstance(h, CQH) and h.pattern is not None
    ]
    assert any("ob_backup" in p for p in patterns)


async def test_onboard_conversation_handles_ob_backup_confirm_callbacks():
    """_OB_BACKUP_CONFIRM state must include a CallbackQueryHandler for ob_backup_confirm:."""
    from telegram.ext import CallbackQueryHandler as CQH
    from flux_bot.channels.commands import _OB_BACKUP_CONFIRM
    handlers = _make_handlers()
    conv = handlers.onboard_conversation()
    assert _OB_BACKUP_CONFIRM in conv.states
    confirm_handlers = conv.states[_OB_BACKUP_CONFIRM]
    patterns = [
        h.pattern.pattern
        for h in confirm_handlers
        if isinstance(h, CQH) and h.pattern is not None
    ]
    assert any("ob_backup_confirm" in p for p in patterns)
