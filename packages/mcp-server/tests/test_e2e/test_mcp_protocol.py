"""Test MCP protocol integration."""
from flux_mcp.server import mcp


async def test_mcp_server_has_tools():
    """Verify MCP server has tools registered."""
    tools = await mcp.list_tools()
    assert len(tools) > 0
    tool_names = [t.name for t in tools]

    # Check transaction tools
    assert "add_transaction" in tool_names
    assert "list_transactions" in tool_names
    assert "search_transactions" in tool_names

    # Check financial tools
    assert "set_budget" in tool_names
    assert "list_budgets" in tool_names
    assert "create_goal" in tool_names
    assert "list_goals" in tool_names

    # Check memory tools
    assert "remember" in tool_names
    assert "recall" in tool_names

    # Check analytics tools
    assert "generate_spending_report" in tool_names
    assert "calculate_financial_health" in tool_names

    # Check profile tools
    assert "update_preferences" in tool_names

    # Check subscription tools
    assert "create_subscription" in tool_names
    assert "list_subscriptions" in tool_names
    assert "toggle_subscription" in tool_names
    assert "delete_subscription" in tool_names
