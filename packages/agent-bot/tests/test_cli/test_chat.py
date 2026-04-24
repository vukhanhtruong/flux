"""Tests for flux CLI: chat subcommand — one-shot and REPL modes."""
from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from flux_bot.cli.wizard import CLI_CHANNEL, CLI_USER_ID
from flux_bot.runner.result import AgentResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repos(*, llm_cfg=..., thread_id="test-thread-123", profile=None):
    """Build mock repos with sensible defaults."""
    from flux_bot.db.llm_config import UserLlmConfig

    if llm_cfg is ...:
        llm_cfg = UserLlmConfig(
            user_id=CLI_USER_ID,
            provider="anthropic",
            model="claude-sonnet-4-6",
            base_url=None,
            api_key="sk-test",
        )

    llm_config_repo = MagicMock()
    llm_config_repo.get = AsyncMock(return_value=llm_cfg)

    session_repo = MagicMock()
    session_repo.get_thread_id = AsyncMock(return_value=thread_id)
    session_repo.delete = AsyncMock()

    profile_repo = MagicMock()
    profile_repo.get_by_user_id = AsyncMock(return_value=profile)

    return llm_config_repo, session_repo, profile_repo


def _make_runner(*, text="Here is your balance.", error=None, thread_id="test-thread-123"):
    runner = MagicMock()
    runner.run = AsyncMock(
        return_value=AgentResult(text=text, thread_id=thread_id, error=error)
    )
    return runner


# ---------------------------------------------------------------------------
# 1. Happy path: one-shot prompt sent, result printed to stdout
# ---------------------------------------------------------------------------

async def test_chat_sends_prompt_to_runner(capsys):
    """One-shot chat: runner.run called with correct args, output printed."""
    from flux_bot.cli.chat import chat

    llm_config_repo, session_repo, profile_repo = _make_repos()
    runner = _make_runner(text="Your balance is $500.")

    rc = await chat(
        "what's my balance?",
        llm_config_repo=llm_config_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        runner=runner,
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert "Your balance is $500." in captured.out

    runner.run.assert_awaited_once()
    call_kwargs = runner.run.call_args.kwargs
    assert call_kwargs["prompt"] == "what's my balance?"
    assert call_kwargs["user_id"] == CLI_USER_ID
    assert call_kwargs["thread_id"] == "test-thread-123"

    # LLM config fetched for CLI_USER_ID
    llm_config_repo.get.assert_awaited_once_with(CLI_USER_ID)
    # Thread ID fetched for CLI_USER_ID + CLI_CHANNEL
    session_repo.get_thread_id.assert_awaited_once_with(CLI_USER_ID, CLI_CHANNEL)


# ---------------------------------------------------------------------------
# 2. Missing LLM config raises CliError
# ---------------------------------------------------------------------------

async def test_chat_missing_llm_config_raises():
    """When no LLM config exists, CliError is raised."""
    from flux_bot.cli.chat import chat
    from flux_bot.cli.wizard import CliError

    llm_config_repo, session_repo, profile_repo = _make_repos(llm_cfg=None)
    runner = _make_runner()

    with pytest.raises(CliError, match="flux config llm"):
        await chat(
            "hello",
            llm_config_repo=llm_config_repo,
            session_repo=session_repo,
            profile_repo=profile_repo,
            runner=runner,
        )

    runner.run.assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. Runner error → return 1 and print to stderr
# ---------------------------------------------------------------------------

async def test_chat_runner_error_returns_nonzero(capsys):
    """When runner returns an error, chat() prints to stderr and returns 1."""
    from flux_bot.cli.chat import chat

    llm_config_repo, session_repo, profile_repo = _make_repos()
    runner = _make_runner(text=None, error="LLM API timeout")

    rc = await chat(
        "hello",
        llm_config_repo=llm_config_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        runner=runner,
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert "LLM API timeout" in captured.err


# ---------------------------------------------------------------------------
# 4. REPL mode: reads multiple lines then EOF → processes each
# ---------------------------------------------------------------------------

async def test_chat_repl_reads_multiple_lines(monkeypatch, capsys):
    """REPL mode processes each non-empty line from stdin then stops at EOF."""
    from flux_bot.cli.chat import chat_repl

    llm_config_repo, session_repo, profile_repo = _make_repos()

    call_count = 0

    async def _fake_run(*, prompt, user_id, thread_id, profile, llm_config, image_path=None):
        nonlocal call_count
        call_count += 1
        return AgentResult(text=f"reply to: {prompt}", thread_id=thread_id)

    runner = MagicMock()
    runner.run = _fake_run

    # Simulate two lines then EOF
    fake_stdin = StringIO("hello\nwhat is my budget?\n")
    monkeypatch.setattr(sys, "stdin", fake_stdin)

    rc = await chat_repl(
        llm_config_repo=llm_config_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        runner=runner,
    )

    assert rc == 0
    assert call_count == 2
    captured = capsys.readouterr()
    assert "reply to: hello" in captured.out
    assert "reply to: what is my budget?" in captured.out


# ---------------------------------------------------------------------------
# 5. --reset path: session_repo.delete called before running
# ---------------------------------------------------------------------------

async def test_chat_reset_deletes_session(capsys):
    """reset=True causes session_repo.delete to be called before running."""
    from flux_bot.cli.chat import chat

    llm_config_repo, session_repo, profile_repo = _make_repos(thread_id="old-thread")
    runner = _make_runner(text="Fresh start.", thread_id="old-thread")

    rc = await chat(
        "hi",
        llm_config_repo=llm_config_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        runner=runner,
        reset=True,
    )

    assert rc == 0
    # delete called with the namespaced key
    session_repo.delete.assert_awaited_once_with(f"thread:{CLI_USER_ID}:{CLI_CHANNEL}")
    runner.run.assert_awaited_once()
