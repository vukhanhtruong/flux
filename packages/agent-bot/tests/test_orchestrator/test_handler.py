"""Tests for make_handle_message, focusing on the thinking-signature retry logic."""

from unittest.mock import AsyncMock, call


from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.runner.sdk import ClaudeResult

_THINKING_ERR = 'API Error: 400 {"error":{"message":"messages.19.content.0: Invalid `signature` in `thinking` block"}}'


def _make_deps(**overrides):
    runner = AsyncMock()
    msg_repo = AsyncMock()
    session_repo = AsyncMock()
    session_repo.get_session_id = AsyncMock(return_value="old-session-id")
    session_repo.delete = AsyncMock()
    session_repo.upsert = AsyncMock()
    profile_repo = AsyncMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=None)
    channels = {}
    deps = dict(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels=channels,
    )
    deps.update(overrides)
    return deps


_MSG = {"id": 70, "user_id": "tg:123", "channel": "telegram", "platform_id": "42", "text": "hello"}


async def test_thinking_signature_error_clears_session_and_retries():
    """When signature error occurs, session is deleted and runner is retried without it."""
    deps = _make_deps()
    deps["runner"].run.side_effect = [
        ClaudeResult(text=None, session_id="old-session-id", error=_THINKING_ERR),
        ClaudeResult(text="Fresh reply", session_id="new-session-id"),
    ]

    handler = make_handle_message(**deps)
    await handler(_MSG)

    # Session must be deleted after the first failure
    deps["session_repo"].delete.assert_awaited_once_with("tg:123")

    # Second call must pass session_id=None
    second_call = deps["runner"].run.call_args_list[1]
    assert second_call == call(
        prompt="hello",
        user_id="tg:123",
        session_id=None,
        image_path=None,
        profile=None,
    )

    # New session must be saved and message marked processed
    deps["session_repo"].upsert.assert_awaited_once_with("tg:123", "new-session-id")
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)
    deps["msg_repo"].mark_failed.assert_not_awaited()


async def test_thinking_signature_error_retry_also_fails_marks_failed():
    """If the retry after clearing the session also errors, the message is marked failed."""
    deps = _make_deps()
    deps["runner"].run.side_effect = [
        ClaudeResult(text=None, session_id="old-session-id", error=_THINKING_ERR),
        ClaudeResult(text=None, session_id=None, error="Some other error"),
    ]

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["session_repo"].delete.assert_awaited_once_with("tg:123")
    deps["msg_repo"].mark_failed.assert_awaited_once_with(70, "Some other error")
    deps["msg_repo"].mark_processed.assert_not_awaited()


async def test_non_signature_error_does_not_retry():
    """Unrelated errors are not retried and the session is not cleared."""
    deps = _make_deps()
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error="Timeout"
    )

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["session_repo"].delete.assert_not_awaited()
    assert deps["runner"].run.call_count == 1
    deps["msg_repo"].mark_failed.assert_awaited_once_with(70, "Timeout")


async def test_success_without_signature_error():
    """Happy path: no retry, session saved, message processed."""
    deps = _make_deps()
    deps["runner"].run.return_value = ClaudeResult(
        text="Great!", session_id="sess-xyz"
    )

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["session_repo"].delete.assert_not_awaited()
    assert deps["runner"].run.call_count == 1
    deps["session_repo"].upsert.assert_awaited_once_with("tg:123", "sess-xyz")
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)


async def test_delivery_failure_sends_error_notification_and_marks_failed():
    """When send_message fails delivering Claude's response, an error notification is sent and message is marked failed."""
    channel = AsyncMock()
    # First call (Claude response) raises, second call (error notification) succeeds
    channel.send_message.side_effect = [Exception("Network error"), None]

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(text="Great response!", session_id="sess-abc")

    handler = make_handle_message(**deps)
    await handler(_MSG)

    # send_message called twice: once for response, once for error notification
    assert channel.send_message.call_count == 2
    deps["msg_repo"].mark_failed.assert_awaited_once()
    deps["msg_repo"].mark_processed.assert_not_awaited()


async def test_delivery_failure_notification_also_fails_still_marks_failed():
    """Even when the error notification delivery also fails, message is marked failed and exception does not propagate."""
    channel = AsyncMock()
    channel.send_message.side_effect = Exception("Network error")

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(text="Great response!", session_id="sess-abc")

    handler = make_handle_message(**deps)
    # Must not raise
    await handler(_MSG)

    deps["msg_repo"].mark_failed.assert_awaited_once()
    deps["msg_repo"].mark_processed.assert_not_awaited()


async def test_token_limit_error_notifies_user_and_marks_failed():
    """Token/quota style errors are surfaced to the user with a friendly message."""
    channel = AsyncMock()

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None,
        session_id=None,
        error="API Error: context window exceeded max_tokens limit",
    )

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["msg_repo"].mark_failed.assert_awaited_once_with(
        70, "API Error: context window exceeded max_tokens limit"
    )
    channel.send_message.assert_awaited_once()
    sent_args = channel.send_message.await_args.args
    assert sent_args[0] == "42"
    assert "limit" in sent_args[1].lower()
    assert "try" in sent_args[1].lower()


async def test_sdk_exit_code_error_notifies_user_with_generic_hint():
    """Opaque SDK failures should still notify users with a retry hint."""
    channel = AsyncMock()
    err = "Command failed with exit code 1 (exit code: 1)\nError output: Check stderr output for details"

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(text=None, session_id=None, error=err)

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["msg_repo"].mark_failed.assert_awaited_once_with(70, err)
    channel.send_message.assert_awaited_once()
    sent_args = channel.send_message.await_args.args
    assert sent_args[0] == "42"
    assert "try again" in sent_args[1].lower()


_AUTH_ERROR = "API Error: 401 authentication_error: Invalid token"


async def test_auth_error_notifies_admin_and_user():
    """Auth errors send admin notification and user-facing message."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)

    assert channel.send_message.call_count == 2
    admin_call = channel.send_message.call_args_list[0]
    assert admin_call.args[0] == "admin-42"
    assert "refresh-token" in admin_call.args[1]
    user_call = channel.send_message.call_args_list[1]
    assert user_call.args[0] == "42"
    assert "temporarily unavailable" in user_call.args[1].lower()
    deps["msg_repo"].mark_failed.assert_awaited_once()


async def test_auth_error_without_admin_chat_id_still_notifies_user():
    """Auth error without admin_chat_id configured still sends user message."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps)
    await handler(_MSG)

    assert channel.send_message.call_count == 1
    user_call = channel.send_message.call_args_list[0]
    assert user_call.args[0] == "42"
    assert "temporarily unavailable" in user_call.args[1].lower()


async def test_auth_error_admin_notification_throttled():
    """Second auth error within throttle window does not re-notify admin."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)
    channel.send_message.reset_mock()

    deps["msg_repo"].mark_failed.reset_mock()
    await handler(_MSG)

    assert channel.send_message.call_count == 1
    user_call = channel.send_message.call_args_list[0]
    assert user_call.args[0] == "42"


async def test_auth_error_admin_notification_after_throttle_expires():
    """Auth error after throttle window expires re-notifies admin."""
    from unittest.mock import patch
    import time

    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)
    channel.send_message.reset_mock()

    with patch("flux_bot.orchestrator.handler.time") as mock_time:
        mock_time.monotonic.return_value = time.monotonic() + 3601
        await handler(_MSG)

    assert channel.send_message.call_count == 2
    admin_call = channel.send_message.call_args_list[0]
    assert admin_call.args[0] == "admin-42"


async def test_non_auth_error_does_not_trigger_admin_notification():
    """Non-auth errors like timeout should not trigger admin notification."""
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error="Timeout"
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)

    channel.send_message.assert_not_awaited()


async def test_auth_error_admin_notification_delivery_fails_gracefully():
    """If admin notification delivery fails, user still gets notified."""
    channel = AsyncMock()
    channel.send_message.side_effect = [
        Exception("Network error"),
        None,
    ]
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)

    assert channel.send_message.call_count == 2
    deps["msg_repo"].mark_failed.assert_awaited_once()


async def test_auth_error_without_platform_id():
    """Auth error for message without platform_id marks failed, no crash."""
    deps = _make_deps()
    deps["runner"].run.return_value = ClaudeResult(
        text=None, session_id=None, error=_AUTH_ERROR
    )

    msg_no_platform = {**_MSG, "platform_id": ""}
    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(msg_no_platform)

    deps["msg_repo"].mark_failed.assert_awaited_once()
