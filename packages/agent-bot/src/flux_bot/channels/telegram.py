"""Telegram channel — receives messages and routes through onboarding or message queue."""

import asyncio
import structlog
import os
from pathlib import Path

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    CommandHandler as TelegramCommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from flux_bot.channels.base import Channel
from flux_bot.channels.commands import CommandHandlers
from flux_bot.channels.formatting import convert_markdown
from flux_bot.db.messages import MessageRepository
from flux_bot.db.profile import ProfileRepository
from flux_bot.db.scheduled_tasks import ScheduledTaskRepository
from flux_bot.db.sessions import SessionRepository

logger = structlog.get_logger(__name__)

_MAX_SEND_RETRIES = 3


class TelegramChannel(Channel):
    def __init__(
        self,
        bot_token: str,
        message_repo: MessageRepository,
        profile_repo: ProfileRepository,
        session_repo: SessionRepository,
        task_repo: ScheduledTaskRepository,
        allow_from: list[str] | None = None,
        image_dir: str = "/tmp/flux-images",
    ):
        self.bot_token = bot_token
        self.message_repo = message_repo
        self.profile_repo = profile_repo
        self.session_repo = session_repo
        self.task_repo = task_repo
        self.allow_from = set(allow_from) if allow_from else None
        self.image_dir = image_dir
        self._app: Application | None = None
        Path(self.image_dir).mkdir(parents=True, exist_ok=True)

    # Telegram message length limit
    _MAX_MESSAGE_LEN = 4096

    async def start(self) -> None:
        # Longer read timeout for long-polling getUpdates (races Telegram's ~5s poll timeout)
        get_updates_request = HTTPXRequest(read_timeout=20, connect_timeout=10)
        # Longer timeouts for regular API calls (send_message etc.) — Claude responses can be large
        request = HTTPXRequest(read_timeout=30, write_timeout=30, connect_timeout=10)
        self._app = (
            Application.builder()
            .token(self.bot_token)
            .get_updates_request(get_updates_request)
            .request(request)
            .build()
        )

        cmds = CommandHandlers(
            profile_repo=self.profile_repo,
            session_repo=self.session_repo,
            task_repo=self.task_repo,
        )

        # ConversationHandlers registered first in group 0 — within a group PTB calls only
        # the first matching handler, so active conversations consume the message before
        # the regular MessageHandler can enqueue it to Claude.
        self._app.add_handler(cmds.settings_conversation())
        self._app.add_handler(cmds.onboard_conversation())

        # Simple one-shot command handlers
        self._app.add_handler(TelegramCommandHandler("help", cmds.cmd_help))
        self._app.add_handler(TelegramCommandHandler("reset", cmds.cmd_reset))
        self._app.add_handler(TelegramCommandHandler("tasks", cmds.cmd_tasks))

        # Regular messages — exclude raw commands so /help etc. don't fall through
        self._app.add_handler(
            MessageHandler(
                (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
                self._handle_message,
            )
        )

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def _send_with_retry(self, chat_id: int, text: str, **kwargs) -> None:
        """Send a single message chunk with exponential-backoff retry on transient errors."""
        delay = 1.0
        for attempt in range(_MAX_SEND_RETRIES):
            try:
                await self._app.bot.send_message(chat_id=chat_id, text=text, **kwargs)
                return
            except (TimedOut, NetworkError) as e:
                if attempt == _MAX_SEND_RETRIES - 1:
                    raise
                logger.warning(
                    f"Telegram send to {chat_id} failed (attempt {attempt + 1}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
                delay *= 2

    async def send_message(self, platform_id: str, text: str) -> None:
        """Send a message to a Telegram user with Markdown formatting."""
        if not self._app:
            return
        converted = convert_markdown(text)
        chunks = [
            converted[i : i + self._MAX_MESSAGE_LEN]
            for i in range(0, len(converted), self._MAX_MESSAGE_LEN)
        ]
        for chunk in chunks:
            await self._send_with_retry(
                int(platform_id), chunk, parse_mode="MarkdownV2"
            )

    async def send_typing_action(self, platform_id: str) -> None:
        """Send a typing indicator to the Telegram user."""
        if self._app:
            await self._app.bot.send_chat_action(chat_id=int(platform_id), action="typing")

    async def send_outbound(self, platform_id: str, text: str, sender: str | None = None) -> None:
        """Deliver an outbound message queued by the agent. Called by OutboundWorker."""
        if not self._app:
            raise RuntimeError("Telegram bot not initialized — cannot deliver outbound message")
        full_text = f"**{sender}**: {text}" if sender else text
        converted = convert_markdown(full_text)
        chunks = [
            converted[i : i + self._MAX_MESSAGE_LEN]
            for i in range(0, len(converted), self._MAX_MESSAGE_LEN)
        ]
        for chunk in chunks:
            await self._send_with_retry(
                int(platform_id), chunk, parse_mode="MarkdownV2"
            )

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message:
            return

        platform_id = str(update.effective_user.id)

        if self.allow_from and platform_id not in self.allow_from:
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        text = update.message.text or update.message.caption
        image_path = None

        if update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            image_path = os.path.join(self.image_dir, f"{photo.file_id}.jpg")
            await file.download_to_drive(image_path)

        if not text and not image_path:
            return

        # Check if user has completed onboarding
        profile = await self.profile_repo.get_by_platform_id("telegram", platform_id)

        if profile is None:
            await self._handle_onboarding(update, platform_id, text or "")
            return

        # User is onboarded — enqueue for Claude
        await self.message_repo.insert(
            user_id=profile.user_id,
            channel="telegram",
            platform_id=platform_id,
            text=text,
            image_path=image_path,
        )
        logger.info(f"Stored message from {profile.user_id}")

    async def _handle_onboarding(
        self, update: Update, platform_id: str, text: str
    ) -> None:
        """Guide new users to the /onboard command."""
        await update.message.reply_text(
            "Welcome to flux!\n\nTo get started, please type /onboard to set up your profile."
        )
