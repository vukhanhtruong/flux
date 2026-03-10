"""Unit tests for ngrok TunnelManager."""
import json
import signal
from unittest.mock import MagicMock, patch

from flux_mcp.ngrok import TunnelManager


async def test_start_tunnel_returns_url():
    """start_tunnel starts ngrok and returns the public URL."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with (
        patch.object(manager, "_start_ngrok_process", return_value=12345),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://abc123.ngrok-free.app"),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
    ):
        result = await manager.start_tunnel("tg:123")

    assert result["status"] == "ok"
    assert result["url"] == "https://abc123.ngrok-free.app"


async def test_start_tunnel_returns_existing():
    """start_tunnel returns existing tunnel if one is already active."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with (
        patch.object(manager, "_start_ngrok_process", return_value=12345),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://abc123.ngrok-free.app"),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
        patch.object(manager, "_is_process_alive", return_value=True),
    ):
        result1 = await manager.start_tunnel("tg:123")
        result2 = await manager.start_tunnel("tg:123")

    assert result1["url"] == result2["url"]


async def test_start_tunnel_reuses_running_ngrok():
    """start_tunnel reuses an already-running ngrok process."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch.object(manager, "_get_existing_tunnel",
                      return_value="https://existing.ngrok-free.app"):
        result = await manager.start_tunnel("tg:123")

    assert result["status"] == "ok"
    assert result["url"] == "https://existing.ngrok-free.app"


async def test_start_tunnel_error():
    """start_tunnel returns error dict on failure."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with (
        patch.object(manager, "_get_existing_tunnel", return_value=None),
        patch.object(manager, "_start_ngrok_process",
                     side_effect=FileNotFoundError("ngrok not found")),
    ):
        result = await manager.start_tunnel("tg:123")

    assert result["status"] == "error"
    assert "ngrok not found" in result["error"]


async def test_stop_tunnel():
    """stop_tunnel kills the ngrok process."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with (
        patch.object(manager, "_start_ngrok_process", return_value=12345),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://abc123.ngrok-free.app"),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
        patch.object(manager, "_kill_ngrok") as mock_kill,
    ):
        await manager.start_tunnel("tg:123")
        result = await manager.stop_tunnel("tg:123")

    assert result["status"] == "ok"
    mock_kill.assert_called_once_with(12345)


async def test_stop_tunnel_no_active():
    """stop_tunnel returns error when no tunnel is active for user."""
    manager = TunnelManager(port=80, timeout_minutes=30)
    result = await manager.stop_tunnel("tg:123")

    assert result["status"] == "error"
    assert "No active tunnel" in result["error"]


async def test_auto_expire():
    """Tunnel auto-expires after timeout by killing the ngrok process."""
    manager = TunnelManager(port=80, timeout_minutes=1)

    with (
        patch.object(manager, "_start_ngrok_process", return_value=12345),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://abc123.ngrok-free.app"),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
    ):
        await manager.start_tunnel("tg:123")

    # Cancel the real expire task and run manually
    expire_task = manager._tunnels["tg:123"].expire_task
    assert expire_task is not None
    expire_task.cancel()

    with patch.object(manager, "_kill_ngrok") as mock_kill:
        await manager._auto_expire("tg:123")

    assert "tg:123" not in manager._tunnels
    mock_kill.assert_called_once_with(12345)


async def test_stale_tunnel_cleaned_up():
    """If tracked process died, start_tunnel creates a new one."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with (
        patch.object(manager, "_start_ngrok_process", return_value=12345),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://abc123.ngrok-free.app"),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
    ):
        await manager.start_tunnel("tg:123")

    # Simulate process death + new tunnel
    with (
        patch.object(manager, "_is_process_alive", return_value=False),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
        patch.object(manager, "_start_ngrok_process", return_value=99999),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://new.ngrok-free.app"),
    ):
        result = await manager.start_tunnel("tg:123")

    assert result["url"] == "https://new.ngrok-free.app"


async def test_start_tunnel_force_new():
    """force_new=True kills existing tunnel and creates a fresh one."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    # First, create a tunnel
    with (
        patch.object(manager, "_start_ngrok_process", return_value=12345),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://old.ngrok-free.app"),
        patch.object(manager, "_get_existing_tunnel", return_value=None),
    ):
        await manager.start_tunnel("tg:123")

    # Now force a new one
    with (
        patch.object(manager, "_kill_all_ngrok") as mock_kill_all,
        patch.object(manager, "_start_ngrok_process", return_value=99999),
        patch.object(manager, "_wait_for_tunnel_url",
                     return_value="https://fresh.ngrok-free.app"),
    ):
        result = await manager.start_tunnel("tg:123", force_new=True)

    assert result["status"] == "ok"
    assert result["url"] == "https://fresh.ngrok-free.app"
    mock_kill_all.assert_awaited_once()


async def test_kill_all_ngrok():
    """_kill_all_ngrok runs pkill to terminate all ngrok processes."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch("flux_mcp.ngrok.subprocess.run") as mock_run:
        await manager._kill_all_ngrok()

    mock_run.assert_called_once_with(["pkill", "-f", "ngrok"], capture_output=True)


# --- Internal method tests ---


def test_start_ngrok_process():
    """_start_ngrok_process launches ngrok as detached subprocess."""
    manager = TunnelManager(port=80, timeout_minutes=30)
    mock_proc = MagicMock()
    mock_proc.pid = 42

    with patch("flux_mcp.ngrok.subprocess.Popen", return_value=mock_proc) as mock_popen:
        pid = manager._start_ngrok_process()

    assert pid == 42
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args
    assert call_args[0][0] == ["ngrok", "http", "80", "--log=stderr"]
    assert call_args[1]["start_new_session"] is True


def test_start_ngrok_process_with_authtoken():
    """_start_ngrok_process includes --authtoken when env var is set."""
    manager = TunnelManager(port=80, timeout_minutes=30)
    mock_proc = MagicMock()
    mock_proc.pid = 42

    with (
        patch("flux_mcp.ngrok.subprocess.Popen", return_value=mock_proc) as mock_popen,
        patch.dict("os.environ", {"NGROK_AUTHTOKEN": "test-token"}),
    ):
        manager._start_ngrok_process()

    cmd = mock_popen.call_args[0][0]
    assert "--authtoken" in cmd
    assert "test-token" in cmd


def test_get_existing_tunnel_returns_https_url():
    """_get_existing_tunnel returns HTTPS tunnel URL from ngrok API."""
    manager = TunnelManager(port=80, timeout_minutes=30)
    api_response = json.dumps({
        "tunnels": [
            {"public_url": "https://abc.ngrok-free.app", "proto": "https"},
        ]
    }).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = api_response
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("flux_mcp.ngrok.urllib.request.urlopen", return_value=mock_resp):
        url = manager._get_existing_tunnel()

    assert url == "https://abc.ngrok-free.app"


def test_get_existing_tunnel_returns_none_on_error():
    """_get_existing_tunnel returns None when ngrok API is not reachable."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch("flux_mcp.ngrok.urllib.request.urlopen", side_effect=OSError("refused")):
        url = manager._get_existing_tunnel()

    assert url is None


def test_get_existing_tunnel_empty_tunnels():
    """_get_existing_tunnel returns None when no tunnels exist."""
    manager = TunnelManager(port=80, timeout_minutes=30)
    api_response = json.dumps({"tunnels": []}).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = api_response
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("flux_mcp.ngrok.urllib.request.urlopen", return_value=mock_resp):
        url = manager._get_existing_tunnel()

    assert url is None


def test_wait_for_tunnel_url_timeout():
    """_wait_for_tunnel_url raises TimeoutError when ngrok doesn't start."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch.object(manager, "_get_existing_tunnel", return_value=None):
        try:
            manager._wait_for_tunnel_url(retries=2, delay=0.01)
            assert False, "Should have raised TimeoutError"
        except TimeoutError as e:
            assert "ngrok tunnel did not start" in str(e)


def test_wait_for_tunnel_url_success():
    """_wait_for_tunnel_url returns URL once available."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch.object(manager, "_get_existing_tunnel",
                      side_effect=[None, None, "https://abc.ngrok-free.app"]):
        url = manager._wait_for_tunnel_url(retries=5, delay=0.01)

    assert url == "https://abc.ngrok-free.app"


def test_kill_ngrok_with_pid():
    """_kill_ngrok sends SIGTERM to the specified PID."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch("flux_mcp.ngrok.os.kill") as mock_kill:
        manager._kill_ngrok(12345)

    mock_kill.assert_called_once_with(12345, signal.SIGTERM)


def test_kill_ngrok_process_already_dead():
    """_kill_ngrok handles already-dead process gracefully."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch("flux_mcp.ngrok.os.kill", side_effect=ProcessLookupError):
        manager._kill_ngrok(12345)  # Should not raise


def test_kill_ngrok_no_pid():
    """_kill_ngrok uses pkill when no PID is tracked."""
    manager = TunnelManager(port=80, timeout_minutes=30)

    with patch("flux_mcp.ngrok.subprocess.run") as mock_run:
        manager._kill_ngrok(0)

    mock_run.assert_called_once_with(["pkill", "-f", "ngrok"], capture_output=True)


def test_is_process_alive_true():
    """_is_process_alive returns True when process exists."""
    with patch("flux_mcp.ngrok.os.kill"):
        assert TunnelManager._is_process_alive(12345) is True


def test_is_process_alive_false():
    """_is_process_alive returns False when process is dead."""
    with patch("flux_mcp.ngrok.os.kill", side_effect=ProcessLookupError):
        assert TunnelManager._is_process_alive(12345) is False


def test_is_process_alive_no_pid():
    """_is_process_alive returns True when no PID is tracked."""
    assert TunnelManager._is_process_alive(0) is True
