"""MCP tools for ngrok tunnel management."""
from __future__ import annotations

from typing import Callable

from fastmcp import FastMCP
from flux_mcp.ngrok import TunnelManager


async def _start_tunnel_impl(manager: TunnelManager, user_id: str) -> dict:
    """Internal implementation for start_web_ui_tunnel tool."""
    return await manager.start_tunnel(user_id)


async def _stop_tunnel_impl(manager: TunnelManager, user_id: str) -> dict:
    """Internal implementation for stop_web_ui_tunnel tool."""
    return await manager.stop_tunnel(user_id)


def register_ngrok_tools(
    mcp: FastMCP,
    get_tunnel_manager: Callable[[], TunnelManager],
    get_session_user_id: Callable[[], str],
):
    @mcp.tool()
    async def start_web_ui_tunnel() -> dict:
        """Start an ngrok tunnel to expose the web UI and return the public URL.

        Use this when the user wants to see their dashboard, view the web interface,
        or access the UI. Returns a public HTTPS URL that expires after 30 minutes.
        The user can ask to stop it early.
        """
        user_id = get_session_user_id()
        return await _start_tunnel_impl(get_tunnel_manager(), user_id)

    @mcp.tool()
    async def stop_web_ui_tunnel() -> dict:
        """Stop the active ngrok tunnel for the web UI.

        Use this when the user asks to close, stop, or disconnect the web UI tunnel.
        """
        user_id = get_session_user_id()
        return await _stop_tunnel_impl(get_tunnel_manager(), user_id)
