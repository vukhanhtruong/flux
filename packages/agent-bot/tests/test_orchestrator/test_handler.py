"""Tests for make_handle_message, focusing on the thinking-signature retry logic."""

from unittest.mock import AsyncMock, call

import pytest

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
