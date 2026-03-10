"""ngrok tunnel manager for exposing web-ui.

Starts ngrok as a detached process (survives MCP server exit) and queries
its local API to retrieve the public tunnel URL.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
import urllib.request
from dataclasses import dataclass


_NGROK_API = "http://localhost:4040/api/tunnels"


@dataclass
class _TunnelInfo:
    pid: int
    url: str
    created_at: float
    expire_task: asyncio.Task | None


class TunnelManager:
    """Manages ngrok tunnels with per-user tracking and auto-expire.

    Uses ngrok CLI as a detached subprocess so the tunnel outlives
    the MCP server process.
    """

    def __init__(self, port: int = 5173, timeout_minutes: int = 30):
        self._port = port
        self._timeout_minutes = timeout_minutes
        self._tunnels: dict[str, _TunnelInfo] = {}

    async def start_tunnel(self, user_id: str) -> dict:
        """Start an ngrok tunnel. Returns existing tunnel if already active."""
        if user_id in self._tunnels:
            info = self._tunnels[user_id]
            if self._is_process_alive(info.pid):
                return {"status": "ok", "url": info.url}
            # Process died — clean up stale entry
            self._tunnels.pop(user_id, None)

        # Check if ngrok is already running (e.g. from a previous MCP session)
        existing_url = await asyncio.to_thread(self._get_existing_tunnel)
        if existing_url:
            self._tunnels[user_id] = _TunnelInfo(
                pid=0, url=existing_url, created_at=time.monotonic(),
                expire_task=None,
            )
            return {"status": "ok", "url": existing_url}

        try:
            pid = await asyncio.to_thread(self._start_ngrok_process)
            url = await asyncio.to_thread(self._wait_for_tunnel_url)

            expire_task = None
            if self._timeout_minutes > 0:
                expire_task = asyncio.create_task(self._auto_expire(user_id))

            self._tunnels[user_id] = _TunnelInfo(
                pid=pid, url=url, created_at=time.monotonic(),
                expire_task=expire_task,
            )
            return {"status": "ok", "url": url}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def stop_tunnel(self, user_id: str) -> dict:
        """Stop an active tunnel for the given user."""
        if user_id not in self._tunnels:
            return {"status": "error", "error": "No active tunnel for this user."}

        info = self._tunnels.pop(user_id)
        if info.expire_task:
            info.expire_task.cancel()
        await asyncio.to_thread(self._kill_ngrok, info.pid)
        return {"status": "ok"}

    def _start_ngrok_process(self) -> int:
        """Start ngrok as a detached process that survives parent exit."""
        authtoken = os.environ.get("NGROK_AUTHTOKEN", "")
        cmd = ["ngrok", "http", str(self._port), "--log=stderr"]
        if authtoken:
            cmd.extend(["--authtoken", authtoken])

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return proc.pid

    def _wait_for_tunnel_url(self, retries: int = 20, delay: float = 0.5) -> str:
        """Poll ngrok local API until tunnel URL is available."""
        for _ in range(retries):
            url = self._get_existing_tunnel()
            if url:
                return url
            time.sleep(delay)
        raise TimeoutError("ngrok tunnel did not start within expected time")

    def _get_existing_tunnel(self) -> str | None:
        """Query ngrok local API for an active tunnel URL."""
        try:
            req = urllib.request.Request(_NGROK_API)
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
                tunnels = data.get("tunnels", [])
                for t in tunnels:
                    public_url = t.get("public_url", "")
                    if public_url.startswith("https://"):
                        return public_url
                    return public_url or None
        except (OSError, json.JSONDecodeError, KeyError):
            return None
        return None

    def _kill_ngrok(self, pid: int) -> None:
        """Kill the ngrok process if it's still alive."""
        if pid <= 0:
            # No specific PID tracked — try to kill any ngrok via pkill
            subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        if pid <= 0:
            return True  # No PID tracked, assume alive
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    async def _auto_expire(self, user_id: str) -> None:
        await asyncio.sleep(self._timeout_minutes * 60)
        if user_id in self._tunnels:
            info = self._tunnels.pop(user_id)
            await asyncio.to_thread(self._kill_ngrok, info.pid)
