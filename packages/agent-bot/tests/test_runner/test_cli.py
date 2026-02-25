import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from flux_bot.runner.cli import ClaudeRunner, ClaudeResult


async def test_run_returns_response_text():
    """ClaudeRunner.run() returns the assistant's text response."""
    mock_output = json.dumps({
        "type": "result",
        "result": "I recorded your lunch expense of 50,000 VND.",
        "session_id": "sess-abc-123",
    })

    with patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        result = await runner.run(prompt="spent 50k lunch", user_id="tg:123")

        assert isinstance(result, ClaudeResult)
        assert result.text == "I recorded your lunch expense of 50,000 VND."
        assert result.session_id == "sess-abc-123"


async def test_run_with_session_resume():
    """ClaudeRunner passes --resume flag when session_id is provided."""
    mock_output = json.dumps({
        "type": "result",
        "result": "Done.",
        "session_id": "sess-abc-123",
    })

    with patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        await runner.run(
            prompt="hello", user_id="tg:123", session_id="sess-old-456"
        )

        call_args = mock_exec.call_args[0]
        assert "--resume" in call_args
        assert "sess-old-456" in call_args


async def test_run_with_image():
    """ClaudeRunner includes image in prompt when image_path is provided."""
    mock_output = json.dumps({
        "type": "result",
        "result": "I see a receipt for coffee.",
        "session_id": "sess-img-789",
    })

    with patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        result = await runner.run(
            prompt="what's on this receipt?",
            user_id="tg:123",
            image_path="/tmp/receipt.jpg",
        )

        assert result.text == "I see a receipt for coffee."


async def test_run_timeout():
    """ClaudeRunner returns error when subprocess times out."""
    with patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = asyncio.TimeoutError()
        mock_proc.kill = MagicMock()
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", timeout=1)
        result = await runner.run(prompt="hello", user_id="tg:123")

        assert result.text is None
        assert result.error is not None
        assert "timeout" in result.error.lower()


async def test_run_nonzero_exit():
    """ClaudeRunner handles non-zero exit code gracefully."""
    with patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Error: model not found")
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        result = await runner.run(prompt="hello", user_id="tg:123")

        assert result.text is None
        assert result.error is not None


async def test_run_nonzero_exit_reads_error_from_stdout_json_when_stderr_empty():
    """ClaudeRunner should extract JSON error text from stdout on non-zero exit."""
    mock_output = json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": True,
        "result": "Invalid API key · Fix external API key",
        "session_id": "sess-err-001",
    })

    with patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        result = await runner.run(prompt="hello", user_id="tg:123")

        assert result.text is None
        assert result.error == "Invalid API key · Fix external API key"


async def test_run_omits_skip_permissions_flag_when_running_as_root():
    """ClaudeRunner must not pass --dangerously-skip-permissions as root."""
    mock_output = json.dumps({
        "type": "result",
        "result": "Done.",
        "session_id": "sess-root-001",
    })

    with (
        patch("os.geteuid", return_value=0),
        patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec,
    ):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        await runner.run(prompt="hello", user_id="tg:123")

        call_args = mock_exec.call_args[0]
        assert "--dangerously-skip-permissions" not in call_args


async def test_run_keeps_skip_permissions_flag_when_not_root():
    """ClaudeRunner should pass --dangerously-skip-permissions for non-root user."""
    mock_output = json.dumps({
        "type": "result",
        "result": "Done.",
        "session_id": "sess-non-root-001",
    })

    with (
        patch("os.geteuid", return_value=1000),
        patch("flux_bot.runner.cli.asyncio.create_subprocess_exec") as mock_exec,
    ):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
        await runner.run(prompt="hello", user_id="tg:123")

        call_args = mock_exec.call_args[0]
        assert "--dangerously-skip-permissions" in call_args


def test_restore_claude_config_from_latest_backup(tmp_path: Path):
    """Restore ~/.claude.json from the newest backup when missing."""
    home = tmp_path / "home"
    backups = home / ".claude" / "backups"
    backups.mkdir(parents=True)
    old = backups / ".claude.json.backup.100"
    latest = backups / ".claude.json.backup.200"
    old.write_text('{"v":"old"}', encoding="utf-8")
    latest.write_text('{"v":"new"}', encoding="utf-8")

    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
    with patch.dict("os.environ", {"HOME": str(home)}, clear=False):
        restored = runner._restore_claude_config_if_missing()

    cfg = home / ".claude.json"
    assert restored is True
    assert cfg.exists()
    assert cfg.read_text(encoding="utf-8") == '{"v":"new"}'


def test_restore_claude_config_no_backup_noop(tmp_path: Path):
    """No-op when ~/.claude.json is missing and there are no backups."""
    home = tmp_path / "home"
    home.mkdir(parents=True)

    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json")
    with patch.dict("os.environ", {"HOME": str(home)}, clear=False):
        restored = runner._restore_claude_config_if_missing()

    assert restored is False
    assert not (home / ".claude.json").exists()
