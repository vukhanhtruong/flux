"""Telegram slash command handlers: /help, /reset, /tasks, /settings, /onboard."""

import logging
import re
import zoneinfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from flux_bot.db.scheduled_tasks import ScheduledTaskRepository
from flux_bot.db.sessions import SessionRepository
from flux_core.db.user_profile_repo import UserProfileRepository

logger = logging.getLogger(__name__)


def _validate_currency(text: str) -> str | None:
    """Return normalised currency code, or None if invalid."""
    normalised = text.strip().upper()
    return normalised if re.match(r"^[A-Z]{2,5}$", normalised) else None


def _validate_timezone(text: str) -> str | None:
    """Return the timezone string if valid, or None if unrecognised."""
    text = text.strip()
    try:
        zoneinfo.ZoneInfo(text)
        return text
    except (zoneinfo.ZoneInfoNotFoundError, KeyError):
        return None


# ConversationHandler states for /settings
_MENU, _EDIT_CURRENCY, _EDIT_TIMEZONE, _EDIT_USERNAME = range(4)

# ConversationHandler states for /onboard
_OB_CURRENCY, _OB_TIMEZONE, _OB_USERNAME = range(3)

HELP_TEXT = """\
Here are some things you can ask me:

📊 *Track Expenses*
  • "Add $12.50 coffee at Starbucks"
  • "I spent 200k on lunch"

💰 *Check Balances*
  • "What's my current balance?"
  • "Show spending this month"

📈 *Reports & Analytics*
  • "Spending breakdown this week"
  • "How much did I spend on food in January?"

📅 *Schedules & Reminders*
  • "Remind me to log expenses every Sunday at 8pm"
  • "Send me a spending summary every Monday morning"

⚙️ Update preferences → /settings
🔄 Start a new session → /reset
📋 View scheduled tasks → /tasks
🚀 Walk through setup & see this help → /onboard\
"""


class CommandHandlers:
    def __init__(
        self,
        profile_repo: UserProfileRepository,
        session_repo: SessionRepository,
        task_repo: ScheduledTaskRepository,
    ):
        self._profile_repo = profile_repo
        self._session_repo = session_repo
        self._task_repo = task_repo

    async def _get_profile(self, update: Update):
        return await self._profile_repo.get_by_platform_id(
            "telegram", str(update.effective_user.id)
        )

    # ------------------------------------------------------------------
    # /help
    # ------------------------------------------------------------------

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

    # ------------------------------------------------------------------
    # /reset
    # ------------------------------------------------------------------

    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        platform_id = str(update.effective_user.id)
        profile = await self._profile_repo.get_by_platform_id("telegram", platform_id)
        if profile is None:
            await update.message.reply_text("No active session to reset.")
            return
        await self._session_repo.delete(profile.user_id)
        await update.message.reply_text(
            "Conversation reset ✓. Your next message starts a fresh session — "
            "your financial data is unchanged."
        )

    # ------------------------------------------------------------------
    # /tasks
    # ------------------------------------------------------------------

    async def cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        platform_id = str(update.effective_user.id)
        profile = await self._profile_repo.get_by_platform_id("telegram", platform_id)
        if profile is None:
            await update.message.reply_text("Please complete setup first.")
            return

        tasks = await self._task_repo.list_by_user(profile.user_id)
        if not tasks:
            await update.message.reply_text(
                "You have no scheduled tasks. Ask me to set one up!"
            )
            return

        tz = zoneinfo.ZoneInfo(profile.timezone)
        lines = ["📋 *Your scheduled tasks:*\n"]
        for i, task in enumerate(tasks, 1):
            prompt = task["prompt"]
            if len(prompt) > 60:
                prompt = prompt[:60] + "…"
            icon = "🔁" if task["schedule_type"] in ("cron", "interval") else "📅"
            next_run_line = ""
            if task.get("next_run_at"):
                local_dt = task["next_run_at"].astimezone(tz)
                next_run_line = f"\n   ⏭ Next: {local_dt.strftime('%a, %b %-d at %H:%M')}"
            lines.append(f"{i}. {prompt}\n   {icon} {task['schedule_type']}{next_run_line}")

        await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")

    # ------------------------------------------------------------------
    # /settings — ConversationHandler
    # ------------------------------------------------------------------

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        platform_id = str(update.effective_user.id)
        profile = await self._profile_repo.get_by_platform_id("telegram", platform_id)
        if profile is None:
            await update.message.reply_text("Please complete setup first.")
            return ConversationHandler.END
        context.user_data["user_id"] = profile.user_id
        await self._send_settings_menu(update, profile)
        return _MENU

    async def _send_settings_menu(self, update: Update, profile) -> None:
        keyboard = [
            [InlineKeyboardButton(f"💱 Currency: {profile.currency}", callback_data="currency")],
            [InlineKeyboardButton(f"🕐 Timezone: {profile.timezone}", callback_data="timezone")],
            [InlineKeyboardButton(f"👤 Username: {profile.username}", callback_data="username")],
            [InlineKeyboardButton("✅ Done", callback_data="done")],
        ]
        text = "⚙️ Settings — tap a field to change it:"
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def _settings_menu_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        query = update.callback_query
        await query.answer()
        if query.data == "done":
            await query.edit_message_text("Settings saved ✓")
            return ConversationHandler.END
        elif query.data == "currency":
            await query.edit_message_text("Enter new currency code (e.g. USD, EUR, JPY):")
            return _EDIT_CURRENCY
        elif query.data == "timezone":
            await query.edit_message_text(
                "Enter your timezone (e.g. UTC, America/New_York, Asia/Ho_Chi_Minh):"
            )
            return _EDIT_TIMEZONE
        elif query.data == "username":
            await query.edit_message_text("Enter a new display name:")
            return _EDIT_USERNAME
        return _MENU

    async def _handle_currency_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        code = _validate_currency(update.message.text)
        if code is None:
            await update.message.reply_text(
                "❌ Invalid currency code. Enter 2–5 uppercase letters (e.g. USD, EUR):"
            )
            return _EDIT_CURRENCY
        user_id = context.user_data["user_id"]
        await self._profile_repo.update(user_id, currency=code)
        await update.message.reply_text(f"✓ Currency updated to {code}")
        profile = await self._profile_repo.get_by_user_id(user_id)
        await self._send_settings_menu(update, profile)
        return _MENU

    async def _handle_timezone_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        tz = _validate_timezone(update.message.text)
        if tz is None:
            await update.message.reply_text(
                f"❌ Unknown timezone '{update.message.text.strip()}'. "
                "Try a standard name like UTC or America/New_York:"
            )
            return _EDIT_TIMEZONE
        user_id = context.user_data["user_id"]
        await self._profile_repo.update(user_id, timezone=tz)
        await update.message.reply_text(f"✓ Timezone updated to {tz}")
        profile = await self._profile_repo.get_by_user_id(user_id)
        await self._send_settings_menu(update, profile)
        return _MENU

    async def _handle_username_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        text = update.message.text.strip()
        user_id = context.user_data["user_id"]
        await self._profile_repo.update(user_id, username=text)
        await update.message.reply_text(f"✓ Username updated to {text}")
        profile = await self._profile_repo.get_by_user_id(user_id)
        await self._send_settings_menu(update, profile)
        return _MENU

    def settings_conversation(self) -> ConversationHandler:
        """Return a configured ConversationHandler for /settings."""
        return ConversationHandler(
            entry_points=[CommandHandler("settings", self.cmd_settings)],
            states={
                _MENU: [CallbackQueryHandler(self._settings_menu_callback)],
                _EDIT_CURRENCY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_currency_input)
                ],
                _EDIT_TIMEZONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_timezone_input)
                ],
                _EDIT_USERNAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_username_input)
                ],
            },
            fallbacks=[CommandHandler("settings", self.cmd_settings)],
            conversation_timeout=600,  # 10 minutes
        )

    # ------------------------------------------------------------------
    # /onboard — linear preferences walkthrough ConversationHandler
    # ------------------------------------------------------------------

    async def cmd_onboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        profile = await self._get_profile(update)
        if profile is None:
            await update.message.reply_text(
                "Please send a message first to complete your initial setup."
            )
            return ConversationHandler.END
        await self._send_ob_currency_prompt(update, profile)
        return _OB_CURRENCY

    async def _send_ob_currency_prompt(self, source, profile) -> None:
        keyboard = [[InlineKeyboardButton("Skip →", callback_data="ob_skip")]]
        await source.message.reply_text(
            "🚀 Let's walk through your preferences. (1/3)\n\n"
            "💱 Currency\n"
            f"Current: {profile.currency}\n\n"
            "Type a new currency code (e.g. USD, VND, EUR), or tap Skip.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _send_ob_timezone_prompt(self, source, profile) -> None:
        keyboard = [[InlineKeyboardButton("Skip →", callback_data="ob_skip")]]
        await source.message.reply_text(
            "🕐 Timezone (2/3)\n\n"
            f"Current: {profile.timezone}\n\n"
            "Type your timezone (e.g. UTC, America/New_York, Asia/Ho_Chi_Minh), or tap Skip.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _send_ob_username_prompt(self, source, profile) -> None:
        keyboard = [[InlineKeyboardButton("Skip →", callback_data="ob_skip")]]
        await source.message.reply_text(
            "👤 Username (3/3)\n\n"
            f"Current: {profile.username}\n\n"
            "Type a new display name, or tap Skip.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _ob_skip_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        profile = await self._get_profile(update)
        await self._send_ob_timezone_prompt(update.callback_query, profile)
        return _OB_TIMEZONE

    async def _ob_skip_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        profile = await self._get_profile(update)
        await self._send_ob_username_prompt(update.callback_query, profile)
        return _OB_USERNAME

    async def _ob_skip_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "✅ Preferences saved!\n\n" + HELP_TEXT, parse_mode="Markdown"
        )
        return ConversationHandler.END

    async def _ob_handle_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = _validate_currency(update.message.text)
        if code is None:
            await update.message.reply_text(
                "❌ Invalid currency code. Enter 2–5 uppercase letters (e.g. USD, EUR):"
            )
            profile = await self._get_profile(update)
            await self._send_ob_currency_prompt(update, profile)
            return _OB_CURRENCY
        profile = await self._get_profile(update)
        await self._profile_repo.update(profile.user_id, currency=code)
        profile = await self._profile_repo.get_by_user_id(profile.user_id)
        await self._send_ob_timezone_prompt(update, profile)
        return _OB_TIMEZONE

    async def _ob_handle_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        tz = _validate_timezone(update.message.text)
        if tz is None:
            await update.message.reply_text(
                f"❌ Unknown timezone '{update.message.text.strip()}'. "
                "Try a standard name like UTC or America/New_York:"
            )
            profile = await self._get_profile(update)
            await self._send_ob_timezone_prompt(update, profile)
            return _OB_TIMEZONE
        profile = await self._get_profile(update)
        await self._profile_repo.update(profile.user_id, timezone=tz)
        profile = await self._profile_repo.get_by_user_id(profile.user_id)
        await self._send_ob_username_prompt(update, profile)
        return _OB_USERNAME

    async def _ob_handle_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip()
        profile = await self._get_profile(update)
        await self._profile_repo.update(profile.user_id, username=text)
        await update.message.reply_text(
            "✅ Preferences saved!\n\n" + HELP_TEXT, parse_mode="Markdown"
        )
        return ConversationHandler.END

    def onboard_conversation(self) -> ConversationHandler:
        """Return a configured ConversationHandler for /onboard."""
        return ConversationHandler(
            entry_points=[CommandHandler("onboard", self.cmd_onboard)],
            states={
                _OB_CURRENCY: [
                    CallbackQueryHandler(self._ob_skip_currency, pattern="^ob_skip$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._ob_handle_currency),
                ],
                _OB_TIMEZONE: [
                    CallbackQueryHandler(self._ob_skip_timezone, pattern="^ob_skip$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._ob_handle_timezone),
                ],
                _OB_USERNAME: [
                    CallbackQueryHandler(self._ob_skip_username, pattern="^ob_skip$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._ob_handle_username),
                ],
            },
            fallbacks=[CommandHandler("onboard", self.cmd_onboard)],
            conversation_timeout=600,
        )
