import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from flux_bot.runner.sdk import ClaudeResult, ClaudeRunner
from flux_core.models.user_profile import UserProfile


def _make_profile(user_id="tg:truong-vu"):
    return UserProfile(
        user_id=user_id, username="truong-vu",
        channel="telegram", platform_id="12345",
        currency="VND", timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )


async def test_run_returns_response_text():
    mock_output = json.dumps({"text": "Recorded", "session_id": "sess-1", "error": None})

    with patch("flux_bot.runner.sdk.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_output.encode(), b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
        result = await runner.run(prompt="hello", user_id="tg:1")

        assert isinstance(result, ClaudeResult)
        assert result.text == "Recorded"
        assert result.session_id == "sess-1"
        assert result.error is None


async def test_run_timeout():
    with patch("flux_bot.runner.sdk.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = asyncio.TimeoutError()
        mock_proc.kill = MagicMock()
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", timeout=1, system_prompt=None)
        result = await runner.run(prompt="hello", user_id="tg:1")

        assert result.text is None
        assert result.error == "Timeout"


async def test_run_nonzero_exit_prefers_stderr():
    with patch("flux_bot.runner.sdk.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"boom")
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
        result = await runner.run(prompt="hello", user_id="tg:1")

        assert result.text is None
        assert result.error == "boom"


async def test_run_nonzero_exit_reads_error_from_stdout_json():
    payload = json.dumps({"error": "Invalid API key"})
    with patch("flux_bot.runner.sdk.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (payload.encode(), b"")
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
        result = await runner.run(prompt="hello", user_id="tg:1")

        assert result.error == "Invalid API key"


async def test_run_invalid_json_output():
    with patch("flux_bot.runner.sdk.asyncio.create_subprocess_exec") as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"not-json", b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
        result = await runner.run(prompt="hello", user_id="tg:1")

        assert result.text is None
        assert result.error == "Failed to parse SDK runner JSON output"


def test_build_runner_env_maps_oauth_token_from_single_var():
    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    with patch.dict(
        "flux_bot.runner.sdk.os.environ",
        {"CLAUDE_AUTH_TOKEN": "sk-ant-oat01-abc", "ANTHROPIC_API_KEY": "old"},
        clear=True,
    ):
        env = runner._build_runner_env()

    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-abc"
    assert "ANTHROPIC_API_KEY" not in env


def test_build_runner_env_maps_api_key_from_single_var():
    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    with patch.dict(
        "flux_bot.runner.sdk.os.environ",
        {"CLAUDE_AUTH_TOKEN": "sk-ant-api03-xyz", "CLAUDE_CODE_OAUTH_TOKEN": "old"},
        clear=True,
    ):
        env = runner._build_runner_env()

    assert env["ANTHROPIC_API_KEY"] == "sk-ant-api03-xyz"
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env


def test_build_temp_mcp_config_injects_user_id(tmp_path):
    base_config = {
        "mcpServers": {
            "finance": {
                "command": "python",
                "args": ["-m", "flux_mcp.server"],
            }
        }
    }
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps(base_config))

    runner = ClaudeRunner(mcp_config_path=str(config_path), system_prompt=None)
    profile = _make_profile()

    temp_path = runner._build_temp_mcp_config(profile)
    try:
        data = json.loads(Path(temp_path).read_text())
        args = data["mcpServers"]["finance"]["args"]
        assert "--user-id" in args
        assert "tg:truong-vu" in args
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_build_system_prompt_includes_profile_context():
    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    profile = _make_profile()

    prompt = runner._build_system_prompt(profile)
    assert "tg:truong-vu" in prompt
    assert "VND" in prompt
    assert "Asia/Ho_Chi_Minh" in prompt
    assert "never ask" in prompt.lower()
