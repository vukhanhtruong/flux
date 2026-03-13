"""E2E tests for financial MCP tools — subscription billing."""
from decimal import Decimal
from uuid import uuid4

from .conftest import extract_json


async def test_process_subscription_billing_creates_transaction(seeded_server):
    """process_subscription_billing creates expense transaction with correct amount."""
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
    sub_id = extract_json(create_result)["id"]

    result = await seeded_server.call_tool(
        "process_subscription_billing", {"subscription_id": sub_id}
    )
    data = extract_json(result)
    assert data["subscription_name"] == "Netflix"
    assert data["amount"] == "15.99"
    assert "transaction_id" in data
    assert "billing_date" in data


async def test_process_subscription_billing_not_found(seeded_server):
    """process_subscription_billing returns error dict for missing subscription."""
    fake_id = str(uuid4())
    result = await seeded_server.call_tool(
        "process_subscription_billing", {"subscription_id": fake_id}
    )
    data = extract_json(result)
    assert "error" in data


async def test_delete_goal(seeded_server):
    """delete_goal removes a goal and returns deleted status."""
    create_result = await seeded_server.call_tool(
        "create_goal", {"name": "Vacation", "target_amount": 5000.0}
    )
    goal_id = extract_json(create_result)["id"]

    result = await seeded_server.call_tool("delete_goal", {"goal_id": goal_id})
    data = extract_json(result)
    assert data["deleted"] is True
    assert data["goal_id"] == goal_id

    # Verify goal no longer in list
    list_result = await seeded_server.call_tool("list_goals", {})
    goals = extract_json(list_result)
    assert all(g["id"] != goal_id for g in goals)


async def test_delete_goal_not_found(seeded_server):
    """delete_goal returns deleted=False for non-existent goal."""
    fake_id = str(uuid4())
    result = await seeded_server.call_tool("delete_goal", {"goal_id": fake_id})
    data = extract_json(result)
    assert data["deleted"] is False


async def test_deposit_to_goal(seeded_server):
    """deposit_to_goal increases goal current_amount."""
    create_result = await seeded_server.call_tool(
        "create_goal", {"name": "Car Fund", "target_amount": 10000.0}
    )
    goal_id = extract_json(create_result)["id"]

    result = await seeded_server.call_tool(
        "deposit_to_goal", {"goal_id": goal_id, "amount": 250.0}
    )
    data = extract_json(result)
    assert data["id"] == goal_id
    assert Decimal(data["current_amount"]) == Decimal("250.0")
    assert data["name"] == "Car Fund"


async def test_deposit_to_goal_not_found(seeded_server):
    """deposit_to_goal returns error for non-existent goal."""
    fake_id = str(uuid4())
    result = await seeded_server.call_tool(
        "deposit_to_goal", {"goal_id": fake_id, "amount": 100.0}
    )
    data = extract_json(result)
    assert "error" in data


async def test_withdraw_from_goal(seeded_server):
    """withdraw_from_goal decreases goal current_amount."""
    create_result = await seeded_server.call_tool(
        "create_goal", {"name": "Emergency", "target_amount": 3000.0}
    )
    goal_id = extract_json(create_result)["id"]

    # Deposit first
    await seeded_server.call_tool(
        "deposit_to_goal", {"goal_id": goal_id, "amount": 500.0}
    )

    result = await seeded_server.call_tool(
        "withdraw_from_goal", {"goal_id": goal_id, "amount": 200.0}
    )
    data = extract_json(result)
    assert data["id"] == goal_id
    assert Decimal(data["current_amount"]) == Decimal("300.0")


async def test_withdraw_from_goal_not_found(seeded_server):
    """withdraw_from_goal returns error for non-existent goal."""
    fake_id = str(uuid4())
    result = await seeded_server.call_tool(
        "withdraw_from_goal", {"goal_id": fake_id, "amount": 100.0}
    )
    data = extract_json(result)
    assert "error" in data


async def test_remove_budget(seeded_server):
    """remove_budget deletes a budget by category."""
    await seeded_server.call_tool(
        "set_budget", {"category": "Food", "monthly_limit": 500.0}
    )

    result = await seeded_server.call_tool("remove_budget", {"category": "Food"})
    data = extract_json(result)
    assert data["deleted"] is True
    assert data["category"] == "Food"

    # Verify budget no longer in list
    list_result = await seeded_server.call_tool("list_budgets", {})
    budgets = extract_json(list_result)
    assert all(b["category"] != "Food" for b in budgets)


async def test_remove_budget_not_found(seeded_server):
    """remove_budget returns deleted=False for non-existent category."""
    result = await seeded_server.call_tool(
        "remove_budget", {"category": "NonExistentCategory"}
    )
    data = extract_json(result)
    assert data["deleted"] is False


async def test_process_subscription_billing_inactive(seeded_server):
    """process_subscription_billing returns error dict for inactive subscription."""
    create_result = await seeded_server.call_tool(
        "create_subscription",
        {
            "name": "Spotify",
            "amount": 9.99,
            "billing_cycle": "monthly",
            "next_date": "2026-04-01",
            "category": "Entertainment",
        },
    )
    sub_id = extract_json(create_result)["id"]
    await seeded_server.call_tool("toggle_subscription", {"subscription_id": sub_id})

    result = await seeded_server.call_tool(
        "process_subscription_billing", {"subscription_id": sub_id}
    )
    data = extract_json(result)
    assert "error" in data
