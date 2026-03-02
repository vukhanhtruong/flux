"""Factory for the handle_message coroutine used by UserQueue."""

import asyncio
import logging

from flux_bot.orchestrator.heartbeat import typing_heartbeat

logger = logging.getLogger(__name__)

_THINKING_SIGNATURE_ERROR = "Invalid `signature` in `thinking` block"
_DELIVERY_ERROR_MSG = "⚠️ I got a response but couldn't send it due to a network issue. Please try again."
_USAGE_LIMIT_ERROR_MSG = (
    "⚠️ I hit an AI usage/context limit and could not finish that request. "
    "Please try a shorter message or try again later."
)
_SDK_UPSTREAM_ERROR_MSG = (
    "⚠️ I couldn't complete that request due to an upstream AI service error "
    "(sometimes caused by usage limits). Please try again."
)
_USAGE_LIMIT_ERROR_PATTERNS = (
    "max_tokens",
    "context window",
    "token limit",
    "rate limit",
    "quota",
    "credit balance",
    "insufficient credits",
)


def _should_notify_usage_limit(error: str) -> bool:
    err = error.lower()
    return any(pattern in err for pattern in _USAGE_LIMIT_ERROR_PATTERNS)


def _error_notification_for_user(error: str) -> str | None:
    err = error.lower()
    if _should_notify_usage_limit(error):
        return _USAGE_LIMIT_ERROR_MSG

    if "command failed with exit code 1" in err and "check stderr output for details" in err:
        return _SDK_UPSTREAM_ERROR_MSG

    return None


def make_handle_message(*, runner, msg_repo, session_repo, profile_repo, channels):
    """Return a handle_message coroutine bound to the given dependencies."""

    async def handle_message(msg: dict) -> None:
        user_id = msg["user_id"]
        platform_id = msg.get("platform_id", "")
        channel_name = msg["channel"]
        channel = channels.get(channel_name)

        profile = await profile_repo.get_by_user_id(user_id)
        session_id = await session_repo.get_session_id(user_id)

        heartbeat_task = None
        if channel and platform_id:
            heartbeat_task = asyncio.create_task(
                typing_heartbeat(channel, platform_id)
            )

        try:
            result = await runner.run(
                prompt=msg.get("text") or "Describe this image",
                user_id=user_id,
                session_id=session_id,
                image_path=msg.get("image_path"),
                profile=profile,
            )

            # Thinking block signatures expire when a session is resumed after a long
            # idle period. Clear the stale session and retry fresh.
            if result.error and _THINKING_SIGNATURE_ERROR in result.error:
                logger.warning(
                    f"Message {msg['id']}: thinking signature expired, "
                    "clearing session and retrying"
                )
                await session_repo.delete(user_id)
                result = await runner.run(
                    prompt=msg.get("text") or "Describe this image",
                    user_id=user_id,
                    session_id=None,
                    image_path=msg.get("image_path"),
                    profile=profile,
                )
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        if result.error is not None:
            await msg_repo.mark_failed(msg["id"], result.error)
            logger.error(f"Message {msg['id']} failed: {result.error}")
            user_msg = _error_notification_for_user(result.error)
            if channel and platform_id and user_msg:
                try:
                    await channel.send_message(platform_id, user_msg)
                except Exception as e:
                    logger.error(f"Could not deliver usage-limit notification to {user_id}: {e}")
            return

        if result.session_id:
            await session_repo.upsert(user_id, result.session_id)

        if channel and result.text and platform_id:
            try:
                await channel.send_message(platform_id, result.text)
            except Exception as e:
                logger.error(f"Delivery failed for message {msg['id']}: {e}")
                try:
                    await channel.send_message(platform_id, _DELIVERY_ERROR_MSG)
                except Exception:
                    logger.error(f"Could not deliver error notification to {user_id}")
                await msg_repo.mark_failed(msg["id"], f"Delivery failed: {e}")
                return

        await msg_repo.mark_processed(msg["id"])
        logger.info(f"Message {msg['id']} processed for {user_id}")

    return handle_message
