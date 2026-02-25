"""Telegram channel — receives messages and routes through onboarding or message queue."""

import logging
import os
from pathlib import Path

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from flux_bot.channels.base import Channel
from flux_bot.db.messages import MessageRepository
from flux_bot.db.onboarding import OnboardingRepository
from flux_bot.onboarding.handler import OnboardingHandler
from flux_core.db.user_profile_repo import UserProfileRepository
from flux_core.models.user_profile import UserProfileCreate

logger = logging.getLogger(__name__)

_ONBOARDING_HANDLER = OnboardingHandler()


class TelegramChannel(Channel):
    def __init__(
        self,
        bot_token: str,
        message_repo: MessageRepository,
        profile_repo: UserProfileRepository,
        onboarding_repo: OnboardingRepository,
        allow_from: list[str] | None = None,
        image_dir: str = "/tmp/flux-images",
    ):
        self.bot_token = bot_token
        self.message_repo = message_repo
        self.profile_repo = profile_repo
        self.onboarding_repo = onboarding_repo
        self.allow_from = set(allow_from) if allow_from else None
        self.image_dir = image_dir
        self._app: Application | None = None
        Path(self.image_dir).mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        self._app = Application.builder().token(self.bot_token).build()
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

    async def send_message(self, platform_id: str, text: str) -> None:
        """Send a message to a Telegram user by their raw numeric platform ID."""
        if self._app:
            await self._app.bot.send_message(chat_id=int(platform_id), text=text)

    async def send_typing_action(self, platform_id: str) -> None:
        """Send a typing indicator to the Telegram user."""
        if self._app:
            await self._app.bot.send_chat_action(chat_id=int(platform_id), action="typing")

    async def send_outbound(self, platform_id: str, text: str, sender: str | None = None) -> None:
        """Deliver an outbound message queued by the agent. Called by OutboundWorker."""
        if not self._app:
            raise RuntimeError("Telegram bot not initialized — cannot deliver outbound message")
        if sender:
            await self._app.bot.send_message(
                chat_id=int(platform_id),
                text=f"*{sender}*: {text}",
                parse_mode="Markdown",
            )
        else:
            await self._app.bot.send_message(chat_id=int(platform_id), text=text)

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
        """Run one step of the onboarding state machine."""
        row = await self.onboarding_repo.get(platform_id, "telegram")

        if row is None:
            # First contact — start onboarding
            result = _ONBOARDING_HANDLER.start()
            await self.onboarding_repo.upsert(platform_id, "telegram", result.next_step)
            await update.message.reply_text(result.reply)
            return

        # Check username availability for the username step
        username_exists = False
        if row["step"] == "username":
            username_exists = await self.profile_repo.username_exists("telegram", text.lower())

        result = _ONBOARDING_HANDLER.handle(
            step=row["step"],
            text=text,
            fields={k: row[k] for k in ("currency", "timezone") if row.get(k)},
            username_exists=username_exists,
        )

        if result.next_step is None:
            # Onboarding complete — create user profile
            f = result.fields
            create = UserProfileCreate(
                username=f["username"],
                channel="telegram",
                platform_id=platform_id,
                currency=f.get("currency", "VND"),
                timezone=f.get("timezone", "Asia/Ho_Chi_Minh"),
            )
            await self.profile_repo.create(create)
            await self.onboarding_repo.delete(platform_id, "telegram")
            logger.info(f"Onboarding complete for tg:{f['username']}")
        else:
            # Advance to next step
            await self.onboarding_repo.upsert(
                platform_id, "telegram", result.next_step,
                currency=result.fields.get("currency"),
                timezone=result.fields.get("timezone"),
            )

        await update.message.reply_text(result.reply)
