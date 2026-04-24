"""Tests for make_handle_message."""

from unittest.mock import AsyncMock, MagicMock, patch
import time

from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.runner.result import AgentResult
from flux_bot.db.llm_config import UserLlmConfig


def _make_llm_config():
    return UserLlmConfig(
        user_id="tg:123",
        provider="anthropic",
        model="claude-sonnet-4-6",
        base_url=None,
        api_key="sk-test-key",
    )


def _make_deps(**overrides):
    runner = AsyncMock()
    runner.run = AsyncMock(return_value=AgentResult(text="ok", thread_id=None))
    msg_repo = AsyncMock()
    session_repo = AsyncMock()
    session_repo.get_thread_id = AsyncMock(return_value=None)
    profile_repo = AsyncMock()
    _profile = MagicMock()
    _profile.user_id = "tg:123"
    _profile.username = "testuser"
    _profile.currency = "USD"
    _profile.timezone = "UTC"
    profile_repo.get_by_user_id = AsyncMock(return_value=_profile)
    llm_config_repo = AsyncMock()
    llm_config_repo.get = AsyncMock(return_value=_make_llm_config())
    channels = {}
    deps = dict(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels=channels,
        llm_config_repo=llm_config_repo,
    )
    deps.update(overrides)
    return deps


_MSG = {"id": 70, "user_id": "tg:123", "channel": "telegram", "platform_id": "42", "text": "hello"}


async def test_success_marks_processed():
    """Happy path: runner succeeds, message processed."""
    deps = _make_deps()
    deps["runner"].run.return_value = AgentResult(text="Great!", thread_id=None)

    handler = make_handle_message(**deps)
    await handler(_MSG)

    assert deps["runner"].run.call_count == 1
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)
    deps["msg_repo"].mark_failed.assert_not_awaited()


async def test_runner_called_with_thread_id_and_llm_config():
    """run() is called with thread_id and llm_config kwargs."""
    llm_cfg = _make_llm_config()
    deps = _make_deps()
    deps["session_repo"].get_thread_id = AsyncMock(return_value="t-abc")
    deps["llm_config_repo"].get = AsyncMock(return_value=llm_cfg)
    deps["runner"].run.return_value = AgentResult(text="deep reply", thread_id="t-abc")

    channel = AsyncMock()
    deps["channels"] = {"telegram": channel}

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["runner"].run.assert_awaited_once_with(
        prompt="hello",
        user_id="tg:123",
        thread_id="t-abc",
        image_path=None,
        profile=deps["profile_repo"].get_by_user_id.return_value,
        llm_config=llm_cfg,
    )
    channel.send_message.assert_awaited_once_with("42", "deep reply")
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)


async def test_no_channel_still_marks_processed():
    """No channel configured: mark_processed is still called."""
    deps = _make_deps(channels={})
    deps["runner"].run.return_value = AgentResult(text="some reply", thread_id=None)

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["runner"].run.assert_awaited_once()
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)
    deps["msg_repo"].mark_failed.assert_not_awaited()


async def test_handler_replies_with_setup_prompt_when_llm_config_missing():
    """No llm_config → setup message sent, mark_processed called, not mark_failed."""
    deps = _make_deps()
    deps["llm_config_repo"].get = AsyncMock(return_value=None)

    channel = AsyncMock()
    deps["channels"] = {"telegram": channel}

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["runner"].run.assert_not_awaited()
    channel.send_message.assert_awaited_once()
    sent_text = channel.send_message.call_args.args[1]
    assert "llm" in sent_text.lower() or "settings" in sent_text.lower()
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)
    deps["msg_repo"].mark_failed.assert_not_awaited()


async def test_handler_sends_onboard_prompt_when_profile_missing():
    """No profile → onboard message sent, mark_processed called, runner not invoked."""
    deps = _make_deps()
    deps["profile_repo"].get_by_user_id = AsyncMock(return_value=None)

    channel = AsyncMock()
    deps["channels"] = {"telegram": channel}

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["runner"].run.assert_not_awaited()
    channel.send_message.assert_awaited_once()
    sent_text = channel.send_message.call_args.args[1]
    assert "profile" in sent_text.lower() or "onboard" in sent_text.lower()
    deps["msg_repo"].mark_processed.assert_awaited_once_with(70)
    deps["msg_repo"].mark_failed.assert_not_awaited()


async def test_llm_config_repo_none_marks_failed():
    """If llm_config_repo is None, mark_failed is called."""
    deps = _make_deps(llm_config_repo=None)

    handler = make_handle_message(**deps)
    await handler(_MSG)

    deps["runner"].run.assert_not_awaited()
    deps["msg_repo"].mark_failed.assert_awaited_once_with(70, "llm_config_repo required")


async def test_delivery_failure_sends_error_notification_and_marks_failed():
    """When send_message fails delivering the response, an error notification is sent and message is marked failed."""
    channel = AsyncMock()
    # First call (response) raises, second call (error notification) succeeds
    channel.send_message.side_effect = [Exception("Network error"), None]

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = AgentResult(text="Great response!", thread_id=None)

    handler = make_handle_message(**deps)
    await handler(_MSG)

    # send_message called twice: once for response, once for error notification
    assert channel.send_message.call_count == 2
    deps["msg_repo"].mark_failed.assert_awaited_once()
    deps["msg_repo"].mark_processed.assert_not_awaited()


async def test_delivery_failure_notification_also_fails_still_marks_failed():
    """Even when the error notification delivery also fails, message is marked failed."""
    channel = AsyncMock()
    channel.send_message.side_effect = Exception("Network error")

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = AgentResult(text="Great response!", thread_id=None)

    handler = make_handle_message(**deps)
    # Must not raise
    await handler(_MSG)

    deps["msg_repo"].mark_failed.assert_awaited_once()
    deps["msg_repo"].mark_processed.assert_not_awaited()


async def test_token_limit_error_notifies_user_and_marks_failed():
    """Token/quota style errors are surfaced to the user with a friendly message."""
    channel = AsyncMock()

    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = AgentResult(
        text=None,
        thread_id=None,
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
    deps["runner"].run.return_value = AgentResult(text=None, thread_id=None, error=err)

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
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error=_AUTH_ERROR
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
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error=_AUTH_ERROR
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
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error=_AUTH_ERROR
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
    channel = AsyncMock()
    deps = _make_deps(channels={"telegram": channel})
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error=_AUTH_ERROR
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
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error="Timeout"
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
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error=_AUTH_ERROR
    )

    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(_MSG)

    assert channel.send_message.call_count == 2
    deps["msg_repo"].mark_failed.assert_awaited_once()


async def test_auth_error_without_platform_id():
    """Auth error for message without platform_id marks failed, no crash."""
    deps = _make_deps()
    deps["runner"].run.return_value = AgentResult(
        text=None, thread_id=None, error=_AUTH_ERROR
    )

    msg_no_platform = {**_MSG, "platform_id": ""}
    handler = make_handle_message(**deps, admin_chat_id="admin-42")
    await handler(msg_no_platform)

    deps["msg_repo"].mark_failed.assert_awaited_once()
