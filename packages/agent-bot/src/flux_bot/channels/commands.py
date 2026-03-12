"""Telegram slash command handlers: /help, /reset, /settings, /onboard."""

import warnings
import structlog
import re
import zoneinfo
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from telegram.warnings import PTBUserWarning

from flux_bot.db.profile import ProfileRepository
from flux_bot.db.scheduled_tasks import ScheduledTaskRepository
from flux_bot.db.sessions import SessionRepository
from flux_core.models.user_profile import UserProfileCreate

logger = structlog.get_logger(__name__)


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


_LOCATION_TZ_MAP: dict[str, list[str]] = {
    # Abbreviations / UTC offsets
    "ict": ["Asia/Ho_Chi_Minh", "Asia/Bangkok", "Asia/Jakarta"],
    "gmt+7": ["Asia/Ho_Chi_Minh", "Asia/Bangkok"],
    "utc+7": ["Asia/Ho_Chi_Minh", "Asia/Bangkok"],
    "jst": ["Asia/Tokyo"],
    "sgt": ["Asia/Singapore"],
    "wib": ["Asia/Jakarta"],
    "est": ["America/New_York"],
    "edt": ["America/New_York"],
    "pst": ["America/Los_Angeles"],
    "pdt": ["America/Los_Angeles"],
    "cst": ["America/Chicago"],
    "gmt": ["UTC", "Europe/London"],
    "bst": ["Europe/London"],
    "cet": ["Europe/Paris", "Europe/Berlin"],
    "aest": ["Australia/Sydney"],
    "ist": ["Asia/Kolkata"],
    # Country / city names (lowercase)
    "vietnam": ["Asia/Ho_Chi_Minh"],
    "viet nam": ["Asia/Ho_Chi_Minh"],
    "ho chi minh": ["Asia/Ho_Chi_Minh"],
    "hanoi": ["Asia/Ho_Chi_Minh"],
    "japan": ["Asia/Tokyo"],
    "tokyo": ["Asia/Tokyo"],
    "singapore": ["Asia/Singapore"],
    "thailand": ["Asia/Bangkok"],
    "bangkok": ["Asia/Bangkok"],
    "indonesia": ["Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura"],
    "jakarta": ["Asia/Jakarta"],
    "india": ["Asia/Kolkata"],
    "china": ["Asia/Shanghai"],
    "beijing": ["Asia/Shanghai"],
    "korea": ["Asia/Seoul"],
    "south korea": ["Asia/Seoul"],
    "seoul": ["Asia/Seoul"],
    "uk": ["Europe/London"],
    "united kingdom": ["Europe/London"],
    "london": ["Europe/London"],
    "germany": ["Europe/Berlin"],
    "berlin": ["Europe/Berlin"],
    "france": ["Europe/Paris"],
    "paris": ["Europe/Paris"],
    "australia": ["Australia/Sydney", "Australia/Melbourne", "Australia/Perth"],
    "sydney": ["Australia/Sydney"],
    "united states": [
        "America/New_York",
        "America/Chicago",
        "America/Los_Angeles",
        "America/Denver",
    ],
    "usa": ["America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver"],
    "us": ["America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver"],
    "new york": ["America/New_York"],
    "los angeles": ["America/Los_Angeles"],
    "chicago": ["America/Chicago"],
    "canada": ["America/Toronto", "America/Vancouver"],
    "brazil": ["America/Sao_Paulo"],
}


def _lookup_timezone_for_location(text: str) -> list[str]:
    """Return up to 4 IANA timezone IDs for a country/city/abbreviation string."""
    key = text.strip().lower()
    if key in _LOCATION_TZ_MAP:
        return _LOCATION_TZ_MAP[key][:4]
    lower = key
    return [tz for tz in sorted(zoneinfo.available_timezones()) if lower in tz.lower()][:4]


def _format_tz_button_label(iana_id: str) -> str:
    """Return friendly label: 'Ho Chi Minh (14:30)'."""
    city = iana_id.split("/")[-1].replace("_", " ")
    local_time = datetime.now(zoneinfo.ZoneInfo(iana_id)).strftime("%H:%M")
    return f"{city} ({local_time})"


# ConversationHandler states for /settings
_MENU, _EDIT_CURRENCY, _EDIT_TIMEZONE, _EDIT_USERNAME = range(4)

# ConversationHandler states for /onboard
_OB_CURRENCY, _OB_TIMEZONE, _OB_USERNAME, _OB_BACKUP, _OB_BACKUP_CONFIRM, _OB_ADVISOR = range(6)

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
🚀 Walk through setup & see this help → /onboard\
"""


class CommandHandlers:
    def __init__(
        self,
        profile_repo: ProfileRepository,
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
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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
                "Enter your city or timezone(e.g. New York, London, UTC):"
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
        if tz is not None:
            user_id = context.user_data["user_id"]
            await self._profile_repo.update(user_id, timezone=tz)
            await update.message.reply_text(f"✓ Timezone updated to {tz}")
            profile = await self._profile_repo.get_by_user_id(user_id)
            await self._send_settings_menu(update, profile)
            return _MENU

        candidates = _lookup_timezone_for_location(update.message.text)
        if candidates:
            buttons = [
                [InlineKeyboardButton(_format_tz_button_label(c), callback_data=f"settings_tz:{c}")]
                for c in candidates
            ]
            if len(candidates) == 1:
                await update.message.reply_text(
                    f"🕐 Found: *{candidates[0]}*\n"
                    f"Current time there: "
                    f"{datetime.now(zoneinfo.ZoneInfo(candidates[0])).strftime('%H:%M, %a %b %-d')}\n\n"
                    "Is this correct?",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            else:
                await update.message.reply_text(
                    "🕐 Found multiple timezones. Pick one:",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            return _EDIT_TIMEZONE

        await update.message.reply_text(
            f"❌ Unknown timezone '{update.message.text.strip()}'. "
            "Try a standard name like UTC or America/New_York, "
            "or type your country or city name:"
        )
        return _EDIT_TIMEZONE

    async def _settings_timezone_button(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await update.callback_query.answer()
        tz = update.callback_query.data.split(":", 1)[1]
        user_id = context.user_data["user_id"]
        await self._profile_repo.update(user_id, timezone=tz)
        await update.callback_query.message.reply_text(f"✓ Timezone updated to {tz}")
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
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PTBUserWarning)
            return ConversationHandler(
                entry_points=[CommandHandler("settings", self.cmd_settings)],
                states={
                    _MENU: [CallbackQueryHandler(self._settings_menu_callback)],
                    _EDIT_CURRENCY: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, self._handle_currency_input
                        )
                    ],
                    _EDIT_TIMEZONE: [
                        CallbackQueryHandler(
                            self._settings_timezone_button, pattern="^settings_tz:"
                        ),
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, self._handle_timezone_input
                        ),
                    ],
                    _EDIT_USERNAME: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, self._handle_username_input
                        )
                    ],
                },
                fallbacks=[CommandHandler("settings", self.cmd_settings)],
                per_message=False,
                conversation_timeout=600,  # 10 minutes
            )

    # ------------------------------------------------------------------
    # /onboard — linear preferences walkthrough ConversationHandler
    # ------------------------------------------------------------------

    async def cmd_onboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        platform_id = str(update.effective_user.id)
        profile = await self._get_profile(update)
        is_new_user = profile is None
        context.user_data["ob_is_new_user"] = is_new_user
        context.user_data["ob_platform_id"] = platform_id
        await self._send_ob_currency_prompt(update, profile)
        return _OB_CURRENCY

    async def _send_ob_currency_prompt(self, source, profile) -> None:
        if profile is None:
            await source.message.reply_text(
                "Let's set up your profile. (1/5)\n\nCurrency — type a code (e.g. USD, VND, EUR):"
            )
        else:
            keyboard = [[InlineKeyboardButton("Skip →", callback_data="ob_skip")]]
            await source.message.reply_text(
                "🚀 Let's walk through your preferences. (1/5)\n\n"
                "💱 Currency\n"
                f"Current: {profile.currency}\n\n"
                "Type a new currency code (e.g. USD, VND, EUR), or tap Skip.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    async def _send_ob_timezone_prompt(self, source, profile) -> None:
        if profile is None:
            await source.message.reply_text(
                "Timezone (2/5)\n\n"
                "Pick one or type another (e.g. America/Chicago), "
                "or type your country or city (e.g. Vietnam, Japan, London):"
            )
        else:
            keyboard = [[InlineKeyboardButton("Skip →", callback_data="ob_skip")]]
            await source.message.reply_text(
                "🕐 Timezone (2/5)\n\n"
                f"Current: {profile.timezone}\n\n"
                "Pick one, tap Skip, or type your country or city.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    async def _send_ob_username_prompt(self, source, profile) -> None:
        if profile is None:
            await source.message.reply_text("Username (3/5)\n\nType a display name:")
        else:
            keyboard = [[InlineKeyboardButton("Skip →", callback_data="ob_skip")]]
            await source.message.reply_text(
                "👤 Username (3/5)\n\n"
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
        await self._send_ob_backup_prompt(update.callback_query)
        return _OB_BACKUP

    async def _ob_handle_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = _validate_currency(update.message.text)
        if code is None:
            await update.message.reply_text(
                "❌ Invalid currency code. Enter 2–5 uppercase letters (e.g. USD, EUR):"
            )
            profile = await self._get_profile(update)
            await self._send_ob_currency_prompt(update, profile)
            return _OB_CURRENCY
        if context.user_data.get("ob_is_new_user"):
            context.user_data["ob_currency"] = code
            await self._send_ob_timezone_prompt(update, None)
        else:
            profile = await self._get_profile(update)
            await self._profile_repo.update(profile.user_id, currency=code)
            profile = await self._profile_repo.get_by_user_id(profile.user_id)
            await self._send_ob_timezone_prompt(update, profile)
        return _OB_TIMEZONE

    async def _ob_handle_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        tz = _validate_timezone(update.message.text)
        if tz is not None:
            if context.user_data.get("ob_is_new_user"):
                context.user_data["ob_timezone"] = tz
                await self._send_ob_username_prompt(update, None)
            else:
                profile = await self._get_profile(update)
                await self._profile_repo.update(profile.user_id, timezone=tz)
                profile = await self._profile_repo.get_by_user_id(profile.user_id)
                await self._send_ob_username_prompt(update, profile)
            return _OB_USERNAME

        candidates = _lookup_timezone_for_location(update.message.text)
        if candidates:
            buttons = [
                [InlineKeyboardButton(_format_tz_button_label(c), callback_data=f"ob_tz:{c}")]
                for c in candidates
            ]
            if len(candidates) == 1:
                await update.message.reply_text(
                    f"🕐 Found: *{candidates[0]}*\n"
                    f"Current time there: "
                    f"{datetime.now(zoneinfo.ZoneInfo(candidates[0])).strftime('%H:%M, %a %b %-d')}\n\n"
                    "Is this correct?",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            else:
                await update.message.reply_text(
                    "🕐 Found multiple timezones. Pick one:",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            return _OB_TIMEZONE

        await update.message.reply_text(
            f"❌ Unknown timezone '{update.message.text.strip()}'. "
            "Try a standard name like UTC, or type your country or city name:"
        )
        profile = await self._get_profile(update)
        await self._send_ob_timezone_prompt(update, profile)
        return _OB_TIMEZONE

    async def _ob_tz_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.callback_query.answer()
        tz = update.callback_query.data.split(":", 1)[1]
        if context.user_data.get("ob_is_new_user"):
            context.user_data["ob_timezone"] = tz
            await self._send_ob_username_prompt(update.callback_query, None)
        else:
            profile = await self._get_profile(update)
            await self._profile_repo.update(profile.user_id, timezone=tz)
            profile = await self._profile_repo.get_by_user_id(profile.user_id)
            await self._send_ob_username_prompt(update.callback_query, profile)
        return _OB_USERNAME

    async def _ob_handle_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip()
        if context.user_data.get("ob_is_new_user"):
            platform_id = context.user_data["ob_platform_id"]
            create = UserProfileCreate(
                username=text,
                channel="telegram",
                platform_id=platform_id,
                currency=context.user_data.get("ob_currency", "VND"),
                timezone=context.user_data.get("ob_timezone", "Asia/Ho_Chi_Minh"),
            )
            await self._profile_repo.create(create)
        else:
            profile = await self._get_profile(update)
            await self._profile_repo.update(profile.user_id, username=text)
        await self._send_ob_backup_prompt(update)
        return _OB_BACKUP

    async def _send_ob_backup_prompt(self, source) -> None:
        keyboard = [
            [InlineKeyboardButton("Daily", callback_data="ob_backup:daily")],
            [InlineKeyboardButton("Weekly", callback_data="ob_backup:weekly")],
            [InlineKeyboardButton("Never", callback_data="ob_backup:never")],
        ]
        await source.message.reply_text(
            "Auto-backup (4/5)\n\n"
            "How often should I automatically backup your data?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _ob_handle_backup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await update.callback_query.answer()
        choice = update.callback_query.data.split(":", 1)[1]

        if choice == "never":
            await update.callback_query.message.reply_text(
                "No auto-backup configured.",
            )
            await self._send_ob_advisor_prompt(update.callback_query)
            return _OB_ADVISOR

        # Check for existing backup tasks
        profile = await self._get_profile(update)
        if profile:
            existing = await self._task_repo.list_by_user(profile.user_id)
            backup_tasks = [t for t in existing if "backup" in t.get("prompt", "").lower()]
            if backup_tasks:
                context.user_data["ob_backup_choice"] = choice
                context.user_data["ob_backup_existing_id"] = backup_tasks[0]["id"]
                existing_type = (
                    "daily" if backup_tasks[0].get("schedule_value") == "0 2 * * *" else "weekly"
                )
                keyboard = [
                    [InlineKeyboardButton(
                        f"Replace ({existing_type} → {choice})",
                        callback_data="ob_backup_confirm:replace",
                    )],
                    [InlineKeyboardButton(
                        "Keep existing",
                        callback_data="ob_backup_confirm:keep",
                    )],
                ]
                await update.callback_query.message.reply_text(
                    f"You already have a {existing_type} backup scheduled.\n"
                    f"Would you like to replace it with {choice}?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return _OB_BACKUP_CONFIRM

        await self._create_backup_task(profile, choice)
        await update.callback_query.message.reply_text(
            f"Auto-backup set to {choice}.",
        )
        await self._send_ob_advisor_prompt(update.callback_query)
        return _OB_ADVISOR

    async def _ob_handle_backup_confirm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await update.callback_query.answer()
        action = update.callback_query.data.split(":", 1)[1]
        choice = context.user_data.get("ob_backup_choice", "daily")
        existing_id = context.user_data.get("ob_backup_existing_id")

        if action == "replace":
            if existing_id:
                await self._task_repo.delete(existing_id)
            profile = await self._get_profile(update)
            await self._create_backup_task(profile, choice)
            msg = f"Auto-backup set to {choice}."
        else:
            msg = "Keeping your existing backup schedule."

        await update.callback_query.message.reply_text(msg)
        await self._send_ob_advisor_prompt(update.callback_query)
        return _OB_ADVISOR

    async def _send_ob_advisor_prompt(self, source) -> None:
        keyboard = [
            [
                InlineKeyboardButton("Sunday evening", callback_data="ob_advisor:sunday"),
                InlineKeyboardButton("Monday morning", callback_data="ob_advisor:monday"),
            ],
            [
                InlineKeyboardButton("Skip", callback_data="ob_advisor:skip"),
            ],
        ]
        await source.message.reply_text(
            "Weekly advisor check-in (5/5)\n\n"
            "Want a weekly financial summary with insights and tips?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _ob_handle_advisor(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await update.callback_query.answer()
        choice = update.callback_query.data.split(":", 1)[1]

        if choice == "skip":
            await update.callback_query.message.reply_text(
                "No weekly check-in configured.\n\n" + HELP_TEXT,
                parse_mode="Markdown",
            )
            return ConversationHandler.END

        profile = await self._get_profile(update)
        if not profile:
            await update.callback_query.message.reply_text(
                "Setup complete!\n\n" + HELP_TEXT, parse_mode="Markdown"
            )
            return ConversationHandler.END

        if choice == "sunday":
            cron_expr = "0 19 * * 0"
            label = "Sunday at 7:00 PM"
        else:  # monday
            cron_expr = "0 9 * * 1"
            label = "Monday at 9:00 AM"

        # Remove existing advisor tasks to prevent duplicates on re-onboard
        existing = await self._task_repo.list_by_user(profile.user_id)
        for t in existing:
            if "weekly financial advisor check-in" in t.get("prompt", "").lower():
                await self._task_repo.delete(t["id"])

        await self._create_advisor_task(profile, cron_expr)
        await update.callback_query.message.reply_text(
            f"Weekly check-in scheduled for {label}.\n\n" + HELP_TEXT,
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    async def _create_advisor_task(self, profile, cron_expr: str) -> None:
        """Create a scheduled task for weekly advisor check-in."""
        from flux_bot.orchestrator.scheduler import compute_next_run

        prompt = (
            "Run a weekly financial advisor check-in for the user:\n"
            "1. Call generate_spending_report for the past 7 days\n"
            "2. Call list_budgets to check budget adherence\n"
            "3. Call list_goals to check goal progress\n"
            "4. Call get_trends comparing this week vs last week\n"
            "5. Summarize findings: highlight wins, flag concerns, give 1-2 actionable tips\n"
            "6. Send the summary to the user via send_message"
        )
        next_run = compute_next_run("cron", cron_expr, profile.timezone or "UTC")
        await self._task_repo.create(
            user_id=profile.user_id,
            prompt=prompt,
            schedule_type="cron",
            schedule_value=cron_expr,
            next_run_at=next_run,
        )

    async def _create_backup_task(self, profile, choice: str) -> None:
        """Create a backup scheduled task for the given frequency choice."""
        if not profile:
            return
        cron_map = {"daily": "0 2 * * *", "weekly": "0 2 * * 0"}
        cron_expr = cron_map[choice]
        from flux_bot.orchestrator.scheduler import compute_next_run
        next_run = compute_next_run("cron", cron_expr, profile.timezone or "UTC")
        await self._task_repo.create(
            user_id=profile.user_id,
            prompt="Create a backup of my data",
            schedule_type="cron",
            schedule_value=cron_expr,
            next_run_at=next_run,
        )

    def onboard_conversation(self) -> ConversationHandler:
        """Return a configured ConversationHandler for /onboard."""
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PTBUserWarning)
            return ConversationHandler(
                entry_points=[CommandHandler("onboard", self.cmd_onboard)],
                states={
                    _OB_CURRENCY: [
                        CallbackQueryHandler(self._ob_skip_currency, pattern="^ob_skip$"),
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, self._ob_handle_currency
                        ),
                    ],
                    _OB_TIMEZONE: [
                        CallbackQueryHandler(self._ob_tz_button, pattern="^ob_tz:"),
                        CallbackQueryHandler(self._ob_skip_timezone, pattern="^ob_skip$"),
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, self._ob_handle_timezone
                        ),
                    ],
                    _OB_USERNAME: [
                        CallbackQueryHandler(self._ob_skip_username, pattern="^ob_skip$"),
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, self._ob_handle_username
                        ),
                    ],
                    _OB_BACKUP: [
                        CallbackQueryHandler(
                            self._ob_handle_backup, pattern="^ob_backup:"
                        ),
                    ],
                    _OB_BACKUP_CONFIRM: [
                        CallbackQueryHandler(
                            self._ob_handle_backup_confirm, pattern="^ob_backup_confirm:"
                        ),
                    ],
                    _OB_ADVISOR: [
                        CallbackQueryHandler(
                            self._ob_handle_advisor, pattern="^ob_advisor:"
                        ),
                    ],
                },
                fallbacks=[CommandHandler("onboard", self.cmd_onboard)],
                per_message=False,
                conversation_timeout=600,
            )
