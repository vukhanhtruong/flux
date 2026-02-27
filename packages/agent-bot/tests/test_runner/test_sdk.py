import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import claude_agent_sdk
from claude_agent_sdk import ResultMessage, SystemMessage
from flux_bot.runner.sdk import ClaudeResult, ClaudeRunner
from flux_core.models.user_profile import UserProfile


def _make_profile(user_id="tg:truong-vu"):
    return UserProfile(
        user_id=user_id,
        username="truong-vu",
        channel="telegram",
        platform_id="12345",
        currency="VND",
        timezone="Asia/Ho_Chi_Minh",
        locale="vi-VN",
    )


def _make_system_init_message(session_id: str) -> SystemMessage:
    return SystemMessage(subtype="init", data={"session_id": session_id})


def _make_result_message(result: str, session_id: str, is_error: bool = False) -> ResultMessage:
    return ResultMessage(
        subtype="success" if not is_error else "error_max_turns",
        duration_ms=100,
        duration_api_ms=90,
        is_error=is_error,
        num_turns=1,
        session_id=session_id,
        result=result,
    )


@pytest.fixture
def mcp_config(tmp_path):
    """Write a minimal MCP config and return its path."""
    config = {"mcpServers": {"flux": {"command": "python", "args": ["-m", "flux_mcp.server"]}}}
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps(config))
    return str(path)


async def test_run_captures_session_and_result(mcp_config):
    system_msg = _make_system_init_message("sess-abc")
    result_msg = _make_result_message("Hello, world!", "sess-abc")

    async def fake_query(prompt, options):
        yield system_msg
        yield result_msg

    runner = ClaudeRunner(mcp_config_path=mcp_config, system_prompt=None)
    with patch("flux_bot.runner.sdk.query", fake_query):
        result = await runner.run(prompt="hello", user_id="tg:1")

    assert result.text == "Hello, world!"
    assert result.session_id == "sess-abc"
    assert result.error is None


async def test_run_result_session_id_from_result_message(mcp_config):
    """ResultMessage.session_id is the authoritative source for session."""
    result_msg = _make_result_message("Done", "new-sess-xyz")

    async def fake_query(prompt, options):
        yield result_msg

    runner = ClaudeRunner(mcp_config_path=mcp_config, system_prompt=None)
    with patch("flux_bot.runner.sdk.query", fake_query):
        result = await runner.run(prompt="hello", user_id="tg:1", session_id="old-sess")

    assert result.text == "Done"
    assert result.session_id == "new-sess-xyz"
    assert result.error is None


async def test_run_error_result_returns_error(mcp_config):
    result_msg = _make_result_message("Something went wrong", "sess-1", is_error=True)

    async def fake_query(prompt, options):
        yield result_msg

    runner = ClaudeRunner(mcp_config_path=mcp_config, system_prompt=None)
    with patch("flux_bot.runner.sdk.query", fake_query):
        result = await runner.run(prompt="hello", user_id="tg:1")

    assert result.text is None
    assert result.error == "Something went wrong"


async def test_run_exception_returns_error(mcp_config):
    async def fake_query(prompt, options):
        raise RuntimeError("Connection refused")
        yield  # make it a generator

    runner = ClaudeRunner(mcp_config_path=mcp_config, system_prompt=None)
    with patch("flux_bot.runner.sdk.query", fake_query):
        result = await runner.run(prompt="hello", user_id="tg:1")

    assert result.text is None
    assert "Connection refused" in result.error


async def test_run_timeout_returns_error(mcp_config):
    async def fake_query(prompt, options):
        await asyncio.sleep(10)
        yield  # make it a generator

    runner = ClaudeRunner(mcp_config_path=mcp_config, timeout=0, system_prompt=None)
    with patch("flux_bot.runner.sdk.query", fake_query):
        result = await runner.run(prompt="hello", user_id="tg:1")

    assert result.text is None
    assert result.error == "Timeout"


def test_build_mcp_servers_injects_user_id(tmp_path):
    base_config = {
        "mcpServers": {
            "flux": {
                "command": "python",
                "args": ["-m", "flux_mcp.server"],
                "env": {"DATABASE_URL": "${DATABASE_URL}"},
            }
        }
    }
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps(base_config))

    runner = ClaudeRunner(mcp_config_path=str(config_path), system_prompt=None)
    profile = _make_profile()

    with patch.dict("os.environ", {"DATABASE_URL": "postgres://localhost/flux"}):
        servers = runner._build_mcp_servers(profile)

    assert "flux" in servers
    args = servers["flux"]["args"]
    assert "--user-id" in args
    assert "tg:truong-vu" in args
    assert servers["flux"]["env"]["DATABASE_URL"] == "postgres://localhost/flux"


def test_build_mcp_servers_no_profile_skips_user_id(tmp_path):
    base_config = {
        "mcpServers": {
            "flux": {
                "command": "python",
                "args": ["-m", "flux_mcp.server"],
            }
        }
    }
    config_path = tmp_path / "mcp.json"
    config_path.write_text(json.dumps(base_config))

    runner = ClaudeRunner(mcp_config_path=str(config_path), system_prompt=None)
    servers = runner._build_mcp_servers(None)

    assert "--user-id" not in servers["flux"]["args"]


def test_build_system_prompt_includes_profile_context():
    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    profile = _make_profile()

    prompt = runner._build_system_prompt(profile)
    assert "tg:truong-vu" in prompt
    assert "VND" in prompt
    assert "Asia/Ho_Chi_Minh" in prompt
    assert "never ask" in prompt.lower()


def test_build_system_prompt_includes_current_datetime():
    import re

    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    profile = _make_profile()  # timezone="Asia/Ho_Chi_Minh"

    prompt = runner._build_system_prompt(profile)

    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", prompt)
    assert "Current date/time" in prompt


def test_setup_env_maps_oauth_token():
    import os

    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    with patch.dict(
        os.environ,
        {"CLAUDE_AUTH_TOKEN": "sk-ant-oat01-abc", "ANTHROPIC_API_KEY": "old"},
        clear=True,
    ):
        runner._setup_env()
        assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "sk-ant-oat01-abc"
        assert "ANTHROPIC_API_KEY" not in os.environ


def test_setup_env_maps_api_key():
    import os

    runner = ClaudeRunner(mcp_config_path="/tmp/mcp.json", system_prompt=None)
    with patch.dict(
        os.environ,
        {"CLAUDE_AUTH_TOKEN": "sk-ant-api03-xyz", "CLAUDE_CODE_OAUTH_TOKEN": "old"},
        clear=True,
    ):
        runner._setup_env()
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-api03-xyz"
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ
