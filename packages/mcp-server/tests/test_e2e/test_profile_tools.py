"""Test update_preferences MCP tool registration."""
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
