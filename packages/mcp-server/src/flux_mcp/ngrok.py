"""ngrok tunnel manager for exposing web-ui."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from pyngrok import ngrok


@dataclass
class _TunnelInfo:
    tunnel: object
    url: str
    expire_task: asyncio.Task | None


class TunnelManager:
    """Manages ngrok tunnels with per-user tracking and auto-expire."""

    def __init__(self, port: int = 5173, timeout_minutes: int = 30):
        self._port = port
        self._timeout_minutes = timeout_minutes
        self._tunnels: dict[str, _TunnelInfo] = {}
        self._auth_set = False

    def _ensure_auth(self) -> None:
        if self._auth_set:
            return
        token = os.environ.get("NGROK_AUTHTOKEN")
        if token:
            ngrok.set_auth_token(token)
        self._auth_set = True

    async def start_tunnel(self, user_id: str) -> dict:
        """Start an ngrok tunnel. Returns existing tunnel if already active."""
        if user_id in self._tunnels:
            info = self._tunnels[user_id]
            return {"status": "ok", "url": info.url}

        try:
            self._ensure_auth()
            tunnel = ngrok.connect(self._port, bind_tls=True)
            url = tunnel.public_url

            expire_task = None
            if self._timeout_minutes >= 0:
                expire_task = asyncio.create_task(self._auto_expire(user_id))

            self._tunnels[user_id] = _TunnelInfo(
                tunnel=tunnel, url=url, expire_task=expire_task
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
        ngrok.disconnect(info.url)
        return {"status": "ok"}

    async def _auto_expire(self, user_id: str) -> None:
        await asyncio.sleep(self._timeout_minutes * 60)
        if user_id in self._tunnels:
            info = self._tunnels.pop(user_id)
            ngrok.disconnect(info.url)
