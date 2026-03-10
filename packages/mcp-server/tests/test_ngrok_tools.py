"""Unit tests for ngrok MCP tools."""
from unittest.mock import AsyncMock

from flux_mcp.tools.ngrok_tools import _start_tunnel_impl, _stop_tunnel_impl


async def test_start_tunnel_impl():
    """start_web_ui_tunnel tool delegates to TunnelManager."""
    mock_manager = AsyncMock()
    mock_manager.start_tunnel.return_value = {
        "status": "ok",
        "url": "https://abc123.ngrok-free.app",
    }

    result = await _start_tunnel_impl(mock_manager, "tg:123")

    assert result["status"] == "ok"
    assert result["url"] == "https://abc123.ngrok-free.app"
    mock_manager.start_tunnel.assert_awaited_once_with("tg:123")


async def test_start_tunnel_impl_error():
    """start_web_ui_tunnel returns error from TunnelManager."""
    mock_manager = AsyncMock()
    mock_manager.start_tunnel.return_value = {
        "status": "error",
        "error": "Auth failed",
    }

    result = await _start_tunnel_impl(mock_manager, "tg:123")

    assert result["status"] == "error"
    assert "Auth failed" in result["error"]


async def test_stop_tunnel_impl():
    """stop_web_ui_tunnel tool delegates to TunnelManager."""
    mock_manager = AsyncMock()
    mock_manager.stop_tunnel.return_value = {"status": "ok"}

    result = await _stop_tunnel_impl(mock_manager, "tg:123")

    assert result["status"] == "ok"
    mock_manager.stop_tunnel.assert_awaited_once_with("tg:123")


async def test_stop_tunnel_impl_no_active():
    """stop_web_ui_tunnel returns error when no tunnel active."""
    mock_manager = AsyncMock()
    mock_manager.stop_tunnel.return_value = {
        "status": "error",
        "error": "No active tunnel for this user.",
    }

    result = await _stop_tunnel_impl(mock_manager, "tg:123")

    assert result["status"] == "error"
    assert "No active tunnel" in result["error"]
