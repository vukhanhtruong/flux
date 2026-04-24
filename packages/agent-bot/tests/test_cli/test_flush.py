"""Tests for flux CLI: flush subcommand."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from flux_bot.cli.wizard import CLI_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_outbound_repo(*, pending: list[dict] | None = None):
    """Build a mock OutboundRepository with configurable pending messages."""
    repo = MagicMock()
    repo.fetch_pending = AsyncMock(return_value=pending or [])
    repo.mark_sent = AsyncMock()
    return repo


def _msg(msg_id: int, user_id: str, text: str) -> dict:
    return {
        "id": msg_id,
        "user_id": user_id,
        "text": text,
        "sender": None,
        "created_at": "2026-04-24T10:00:00",
    }


# ---------------------------------------------------------------------------
# 1. Happy path: pending messages printed and marked sent
# ---------------------------------------------------------------------------

async def test_flush_prints_and_marks_sent(capsys):
    """Pending messages for the user are printed to stdout and marked sent."""
    from flux_bot.cli.flush import flush

    msgs = [
        _msg(1, CLI_USER_ID, "Your subscription renewed."),
        _msg(2, CLI_USER_ID, "Budget alert: 80% used."),
    ]
    repo = _make_outbound_repo(pending=msgs)

    count = await flush(repo, user_id=CLI_USER_ID)

    assert count == 2
    captured = capsys.readouterr()
    assert "Your subscription renewed." in captured.out
    assert "Budget alert: 80% used." in captured.out

    repo.mark_sent.assert_awaited()
    assert repo.mark_sent.await_count == 2
    # Called with each message ID
    call_ids = {call.args[0] for call in repo.mark_sent.await_args_list}
    assert call_ids == {1, 2}


# ---------------------------------------------------------------------------
# 2. No pending messages → prints notice
# ---------------------------------------------------------------------------

async def test_flush_no_messages_prints_notice(capsys):
    """When no pending messages exist, a notice is printed and count is 0."""
    from flux_bot.cli.flush import flush

    repo = _make_outbound_repo(pending=[])

    count = await flush(repo, user_id=CLI_USER_ID)

    assert count == 0
    captured = capsys.readouterr()
    assert "No pending messages." in captured.out
    repo.mark_sent.assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. Messages for other users are filtered out
# ---------------------------------------------------------------------------

async def test_flush_filters_by_user_id(capsys):
    """Only messages for the specified user_id are printed and marked sent."""
    from flux_bot.cli.flush import flush

    msgs = [
        _msg(10, CLI_USER_ID, "Your message."),
        _msg(11, "tg:999", "Someone else's message."),
        _msg(12, "tg:888", "Another user's message."),
    ]
    repo = _make_outbound_repo(pending=msgs)

    count = await flush(repo, user_id=CLI_USER_ID)

    assert count == 1
    captured = capsys.readouterr()
    assert "Your message." in captured.out
    assert "Someone else's message." not in captured.out
    assert "Another user's message." not in captured.out

    # Only message ID 10 marked sent
    repo.mark_sent.assert_awaited_once_with(10)


# ---------------------------------------------------------------------------
# 4. flush with a non-default user_id
# ---------------------------------------------------------------------------

async def test_flush_custom_user_id(capsys):
    """flush() with a custom user_id only processes that user's messages."""
    from flux_bot.cli.flush import flush

    msgs = [
        _msg(20, "tg:999", "Agent says hello."),
        _msg(21, CLI_USER_ID, "CLI user message."),
    ]
    repo = _make_outbound_repo(pending=msgs)

    count = await flush(repo, user_id="tg:999")

    assert count == 1
    captured = capsys.readouterr()
    assert "Agent says hello." in captured.out
    assert "CLI user message." not in captured.out
    repo.mark_sent.assert_awaited_once_with(20)
