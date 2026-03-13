"""E2E tests for MCP protocol with seeded SQLite+zvec."""
from flux_mcp.server import mcp

from .conftest import extract_json


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


async def test_add_and_list_transaction_flow(seeded_server):
    """Full E2E flow: add_transaction then list_transactions."""
    # Add a transaction
    add_result = await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-01",
            "amount": 42.50,
            "category": "Food",
            "description": "Lunch at restaurant",
            "transaction_type": "expense",
        },
    )
    add_data = extract_json(add_result)
    assert add_data["category"] == "Food"
    assert add_data["amount"] == "42.5"
    txn_id = add_data["id"]
    assert txn_id  # UUID string

    # List transactions
    list_result = await seeded_server.call_tool(
        "list_transactions", {"limit": 10}
    )
    list_data = extract_json(list_result)
    assert isinstance(list_data, list)
    assert len(list_data) >= 1
    ids = [t["id"] for t in list_data]
    assert txn_id in ids


async def test_multiple_transactions_ordering(seeded_server):
    """Add multiple transactions and verify list ordering (newest first)."""
    dates = ["2026-01-01", "2026-03-15", "2026-02-01"]
    for d in dates:
        await seeded_server.call_tool(
            "add_transaction",
            {
                "date": d,
                "amount": 10.00,
                "category": "Food",
                "description": f"Txn on {d}",
                "transaction_type": "expense",
            },
        )

    list_result = await seeded_server.call_tool(
        "list_transactions", {"limit": 50}
    )
    list_data = extract_json(list_result)
    assert len(list_data) >= 3
    # Should be ordered by date descending
    list_dates = [t["date"] for t in list_data]
    assert list_dates == sorted(list_dates, reverse=True)


async def test_budget_flow(seeded_server):
    """Full E2E flow: set_budget then list_budgets."""
    set_result = await seeded_server.call_tool(
        "set_budget",
        {
            "category": "Food",
            "monthly_limit": 500.00,
        },
    )
    set_data = extract_json(set_result)
    assert set_data["category"] == "Food"
    assert float(set_data["monthly_limit"]) == 500.00

    # List budgets
    list_result = await seeded_server.call_tool("list_budgets", {})
    list_data = extract_json(list_result)
    assert isinstance(list_data, list)
    assert len(list_data) >= 1
    categories = [b["category"] for b in list_data]
    assert "Food" in categories


async def test_goal_flow(seeded_server):
    """Full E2E flow: create_goal then list_goals."""
    create_result = await seeded_server.call_tool(
        "create_goal",
        {
            "name": "Emergency Fund",
            "target_amount": 10000.00,
        },
    )
    create_data = extract_json(create_result)
    assert create_data["name"] == "Emergency Fund"
    assert float(create_data["target_amount"]) == 10000.00

    # List goals
    list_result = await seeded_server.call_tool("list_goals", {})
    list_data = extract_json(list_result)
    assert isinstance(list_data, list)
    assert len(list_data) >= 1
    names = [g["name"] for g in list_data]
    assert "Emergency Fund" in names


async def test_subscription_flow(seeded_server):
    """Full E2E flow: create, list, toggle, delete subscription."""
    # Create
    create_result = await seeded_server.call_tool(
        "create_subscription",
        {
            "name": "Netflix",
            "amount": 15.99,
            "billing_cycle": "monthly",
            "next_date": "2026-04-01",
            "category": "Entertainment",
        },
    )
    create_data = extract_json(create_result)
    assert create_data["name"] == "Netflix"
    sub_id = create_data["id"]

    # List
    list_result = await seeded_server.call_tool(
        "list_subscriptions", {"active_only": True}
    )
    list_data = extract_json(list_result)
    assert any(s["id"] == sub_id for s in list_data)

    # Toggle inactive
    toggle_result = await seeded_server.call_tool(
        "toggle_subscription", {"subscription_id": sub_id}
    )
    toggle_data = extract_json(toggle_result)
    assert toggle_data["active"] is False

    # Delete
    delete_result = await seeded_server.call_tool(
        "delete_subscription", {"subscription_id": sub_id}
    )
    delete_data = extract_json(delete_result)
    assert delete_data["deleted"] is True


async def test_dual_write_transaction_adds_to_both_stores(seeded_server):
    """Verify that add_transaction writes to both SQLite and vector store."""
    add_result = await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-07",
            "amount": 25.00,
            "category": "Health",
            "description": "Pharmacy",
            "transaction_type": "expense",
        },
    )
    add_data = extract_json(add_result)
    txn_id = add_data["id"]

    # Verify in SQLite via list
    list_result = await seeded_server.call_tool(
        "list_transactions", {"limit": 50}
    )
    list_data = extract_json(list_result)
    assert txn_id in [t["id"] for t in list_data]

    # Verify embedding was created (mock was called)
    import flux_core.infrastructure as infra
    svc = infra._embedding_service
    svc.embed.assert_called()
