"""Factory for the handle_message coroutine used by UserQueue."""

import asyncio
import time

import structlog

from flux_bot.orchestrator.heartbeat import typing_heartbeat

logger = structlog.get_logger(__name__)

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


_AUTH_ERROR_PATTERNS = (
    "authentication_error",
    "unauthorized",
    "401",
    "token expired",
    "invalid token",
    "invalid_token",
)

_AUTH_ERROR_USER_MSG = (
    "⚠️ I'm temporarily unavailable due to an authentication issue. "
    "The admin has been notified."
)

_AUTH_ERROR_ADMIN_MSG = (
    "⚠️ Claude authentication token has expired.\n"
    "Run this command to refresh:\n\n"
    "npx @flux-finance/cli refresh-token"
)

_AUTH_NOTIFY_THROTTLE_SECS = 3600  # 1 hour


_SESSION_RETRY_PATTERNS = (
    _THINKING_SIGNATURE_ERROR.lower(),
    "command failed with exit code 1",
)


def _matches_any(error: str, patterns: tuple[str, ...]) -> bool:
    """Check if error (case-insensitive) contains any of the given patterns."""
    err = error.lower()
    return any(p in err for p in patterns)


def _is_auth_error(error: str) -> bool:
    return _matches_any(error, _AUTH_ERROR_PATTERNS)


def _should_retry_without_session(error: str) -> bool:
    return _matches_any(error, _SESSION_RETRY_PATTERNS)


def _should_notify_usage_limit(error: str) -> bool:
    return _matches_any(error, _USAGE_LIMIT_ERROR_PATTERNS)


def _error_notification_for_user(error: str) -> str | None:
    if _should_notify_usage_limit(error):
        return _USAGE_LIMIT_ERROR_MSG

    err = error.lower()
    if "command failed with exit code 1" in err and "check stderr output for details" in err:
        return _SDK_UPSTREAM_ERROR_MSG

    return None


async def _safe_send(channel, target: str, text: str, context: str) -> None:
    """Send a message via channel, logging errors without raising."""
    try:
        await channel.send_message(target, text)
    except Exception as e:
        logger.error(f"{context}: {e}")


def make_handle_message(
    *, runner, msg_repo, session_repo, profile_repo, channels, admin_chat_id=None
):
    """Return a handle_message coroutine bound to the given dependencies."""

    last_admin_notify = -_AUTH_NOTIFY_THROTTLE_SECS

    async def handle_message(msg: dict) -> None:
        user_id = msg["user_id"]
        platform_id = msg.get("platform_id", "")
        channel_name = msg["channel"]
        channel = channels.get(channel_name)

        profile, session_id = await asyncio.gather(
            profile_repo.get_by_user_id(user_id),
            session_repo.get_session_id(user_id),
        )

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

            # Stale/invalid sessions cause CLI exit code 1 or thinking signature
            # errors. Clear the session and retry fresh.
            if result.error and session_id and _should_retry_without_session(result.error):
                logger.warning(
                    f"Message {msg['id']}: session error (likely stale), "
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

            if _is_auth_error(result.error):
                # Notify admin (throttled)
                if admin_chat_id and channel:
                    nonlocal last_admin_notify
                    now = time.monotonic()
                    if now - last_admin_notify >= _AUTH_NOTIFY_THROTTLE_SECS:
                        last_admin_notify = now
                        await _safe_send(
                            channel, admin_chat_id, _AUTH_ERROR_ADMIN_MSG,
                            "Could not notify admin",
                        )
                # Notify user
                if channel and platform_id:
                    await _safe_send(
                        channel, platform_id, _AUTH_ERROR_USER_MSG,
                        f"Could not notify user {user_id}",
                    )
            else:
                user_msg = _error_notification_for_user(result.error)
                if channel and platform_id and user_msg:
                    await _safe_send(
                        channel, platform_id, user_msg,
                        f"Could not deliver error notification to {user_id}",
                    )
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
