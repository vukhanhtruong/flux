"""Test update_preferences MCP tool registration."""
import json

from flux_mcp.server import mcp


async def test_update_preferences_tool_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "update_preferences" in tool_names


async def test_update_preferences_tool_has_correct_params():
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "update_preferences")
    params = tool.parameters.get("properties", {})
    assert "currency" in params
    assert "timezone" in params
    assert "username" in params


def _extract_json(tool_result):
    assert len(tool_result.content) > 0
    return json.loads(tool_result.content[0].text)


async def test_update_preferences_read_only(seeded_server):
    """Calling update_preferences with no params returns current profile."""
    result = await seeded_server.call_tool("update_preferences", {})
    data = _extract_json(result)
    assert "currency" in data
    assert "timezone" in data
    assert "username" in data
    assert "user_id" in data


async def test_update_preferences_write(seeded_server):
    """Calling update_preferences with currency updates the profile."""
    result = await seeded_server.call_tool(
        "update_preferences", {"currency": "EUR"}
    )
    data = _extract_json(result)
    assert data["currency"] == "EUR"


async def test_update_preferences_invalid_timezone(seeded_server):
    """Calling update_preferences with invalid timezone returns error dict."""
    result = await seeded_server.call_tool(
        "update_preferences", {"timezone": "Invalid/NotReal"}
    )
    data = _extract_json(result)
    assert "error" in data
