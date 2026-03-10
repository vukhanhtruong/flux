"""Unit tests for ngrok TunnelManager."""
import asyncio
from unittest.mock import MagicMock, patch

from flux_mcp.ngrok import TunnelManager


async def test_start_tunnel_returns_url():
    """start_tunnel creates a tunnel and returns the public URL."""
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = "https://abc123.ngrok-free.app"

    with patch("flux_mcp.ngrok.ngrok") as mock_ngrok:
        mock_ngrok.connect.return_value = mock_tunnel

        manager = TunnelManager(port=5173, timeout_minutes=30)
        result = await manager.start_tunnel("tg:123")

    assert result["status"] == "ok"
    assert result["url"] == "https://abc123.ngrok-free.app"
    mock_ngrok.connect.assert_called_once_with(5173, bind_tls=True)


async def test_start_tunnel_returns_existing():
    """start_tunnel returns existing tunnel if one is already active for user."""
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = "https://abc123.ngrok-free.app"

    with patch("flux_mcp.ngrok.ngrok") as mock_ngrok:
        mock_ngrok.connect.return_value = mock_tunnel

        manager = TunnelManager(port=5173, timeout_minutes=30)
        result1 = await manager.start_tunnel("tg:123")
        result2 = await manager.start_tunnel("tg:123")

    assert result1["url"] == result2["url"]
    mock_ngrok.connect.assert_called_once()


async def test_start_tunnel_error():
    """start_tunnel returns error dict on failure."""
    with patch("flux_mcp.ngrok.ngrok") as mock_ngrok:
        mock_ngrok.connect.side_effect = Exception("Auth failed")

        manager = TunnelManager(port=5173, timeout_minutes=30)
        result = await manager.start_tunnel("tg:123")

    assert result["status"] == "error"
    assert "Auth failed" in result["error"]


async def test_stop_tunnel():
    """stop_tunnel disconnects an active tunnel."""
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = "https://abc123.ngrok-free.app"

    with patch("flux_mcp.ngrok.ngrok") as mock_ngrok:
        mock_ngrok.connect.return_value = mock_tunnel

        manager = TunnelManager(port=5173, timeout_minutes=30)
        await manager.start_tunnel("tg:123")
        result = await manager.stop_tunnel("tg:123")

    assert result["status"] == "ok"
    mock_ngrok.disconnect.assert_called_once_with(mock_tunnel.public_url)


async def test_stop_tunnel_no_active():
    """stop_tunnel returns error when no tunnel is active for user."""
    manager = TunnelManager(port=5173, timeout_minutes=30)
    result = await manager.stop_tunnel("tg:123")

    assert result["status"] == "error"
    assert "No active tunnel" in result["error"]


async def test_auto_expire():
    """Tunnel auto-expires after timeout."""
    mock_tunnel = MagicMock()
    mock_tunnel.public_url = "https://abc123.ngrok-free.app"

    with patch("flux_mcp.ngrok.ngrok") as mock_ngrok:
        mock_ngrok.connect.return_value = mock_tunnel

        manager = TunnelManager(port=5173, timeout_minutes=0)
        await manager.start_tunnel("tg:123")

        await asyncio.sleep(0.1)

    assert "tg:123" not in manager._tunnels
    mock_ngrok.disconnect.assert_called_once_with(mock_tunnel.public_url)


async def test_set_authtoken():
    """TunnelManager sets authtoken if NGROK_AUTHTOKEN env var is present."""
    with (
        patch("flux_mcp.ngrok.ngrok") as mock_ngrok,
        patch.dict("os.environ", {"NGROK_AUTHTOKEN": "test-token-123"}),
    ):
        mock_tunnel = MagicMock()
        mock_tunnel.public_url = "https://abc123.ngrok-free.app"
        mock_ngrok.connect.return_value = mock_tunnel

        manager = TunnelManager(port=5173, timeout_minutes=30)
        await manager.start_tunnel("tg:123")

    mock_ngrok.set_auth_token.assert_called_once_with("test-token-123")
