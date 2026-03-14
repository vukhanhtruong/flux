"""E2E tests for savings MCP tools."""
from decimal import Decimal

from .conftest import extract_json


async def _assert_task_exists(server, asset_id):
    """Assert a scheduled task exists for the given asset."""
    tasks = extract_json(await server.call_tool("list_scheduled_tasks", {}))
    assert asset_id in [t["asset_id"] for t in tasks["tasks"]]


async def _assert_task_deleted(server, asset_id):
    """Assert no scheduled task exists for the given asset."""
    tasks = extract_json(await server.call_tool("list_scheduled_tasks", {}))
    assert asset_id not in [t["asset_id"] for t in tasks["tasks"]]


async def test_create_savings_deposit_defaults_start_date(seeded_server):
    """create_savings_deposit with start_date=None defaults to today."""
    result = await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "Term Deposit",
            "amount": 10000.0,
            "interest_rate": 5.0,
            "compound_frequency": "monthly",
            "maturity_date": "2028-03-07",
            "category": "savings",
        },
    )
    data = extract_json(result)
    assert data["name"] == "Term Deposit"
    assert Decimal(data["amount"]) == Decimal("10000")
    assert data["active"] is True
    assert "id" in data


async def test_list_savings(seeded_server):
    """list_savings returns correct response format after seeding."""
    await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "My Savings",
            "amount": 5000.0,
            "interest_rate": 3.0,
            "compound_frequency": "monthly",
            "maturity_date": "2027-06-01",
            "category": "savings",
        },
    )
    result = await seeded_server.call_tool("list_savings", {"active_only": True})
    data = extract_json(result)
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "id" in item
    assert "name" in item
    assert "amount" in item
    assert "interest_rate" in item
    assert "compound_frequency" in item
    assert "next_date" in item
    assert "active" in item


async def test_process_savings_interest(seeded_server):
    """process_savings_interest applies interest and returns updated balance."""
    create_result = await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "Interest Test",
            "amount": 10000.0,
            "interest_rate": 12.0,
            "compound_frequency": "monthly",
            "maturity_date": "2028-01-01",
            "category": "savings",
        },
    )
    asset_id = extract_json(create_result)["id"]
    result = await seeded_server.call_tool(
        "process_savings_interest", {"asset_id": asset_id}
    )
    data = extract_json(result)
    # 10000 * (12/100/12) = 100.00
    assert data["interest_applied"] == "100.00"
    assert data["new_balance"] == "10100.00"
    assert data["matured"] is False


async def test_close_savings_early(seeded_server):
    """close_savings_early deactivates asset and removes scheduler task."""
    create_result = await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "Early Close",
            "amount": 5000.0,
            "interest_rate": 4.0,
            "compound_frequency": "monthly",
            "maturity_date": "2028-01-01",
            "category": "savings",
        },
    )
    asset_id = extract_json(create_result)["id"]

    await _assert_task_exists(seeded_server, asset_id)

    result = await seeded_server.call_tool(
        "close_savings_early", {"asset_id": asset_id}
    )
    data = extract_json(result)
    assert data["active"] is False
    assert data["status"] == "closed_early"
    assert data["name"] == "Early Close"
    # Verify asset no longer in active list
    list_result = await seeded_server.call_tool("list_savings", {"active_only": True})
    list_data = extract_json(list_result)
    ids = [s["id"] for s in list_data]
    assert asset_id not in ids
    await _assert_task_deleted(seeded_server, asset_id)


async def test_withdraw_savings(seeded_server):
    """withdraw_savings creates income transaction, deactivates asset, and removes tasks."""
    create_result = await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "Withdraw Test",
            "amount": 8000.0,
            "interest_rate": 5.0,
            "compound_frequency": "monthly",
            "maturity_date": "2028-01-01",
            "category": "savings",
        },
    )
    asset_id = extract_json(create_result)["id"]

    await _assert_task_exists(seeded_server, asset_id)

    result = await seeded_server.call_tool(
        "withdraw_savings", {"asset_id": asset_id}
    )
    data = extract_json(result)
    assert Decimal(data["withdrawn_amount"]) == Decimal("8000")
    assert data["asset_name"] == "Withdraw Test"
    await _assert_task_deleted(seeded_server, asset_id)


async def test_create_savings_deposit_at_maturity(seeded_server):
    """create_savings_deposit with at_maturity sets next_date to maturity_date."""
    result = await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "Fixed Deposit",
            "amount": 200000000.0,
            "interest_rate": 5.0,
            "compound_frequency": "at_maturity",
            "maturity_date": "2026-06-14",
            "category": "savings",
            "start_date": "2026-03-14",
        },
    )
    data = extract_json(result)
    assert data["next_date"] == "2026-06-14"
    assert data["compound_frequency"] == "at_maturity"
    assert data["active"] is True


async def test_delete_savings(seeded_server):
    """delete_savings removes both asset and scheduler task."""
    create_result = await seeded_server.call_tool(
        "create_savings_deposit",
        {
            "name": "Delete Me",
            "amount": 1000.0,
            "interest_rate": 2.0,
            "compound_frequency": "yearly",
            "maturity_date": "2028-01-01",
            "category": "savings",
        },
    )
    asset_id = extract_json(create_result)["id"]

    await _assert_task_exists(seeded_server, asset_id)

    result = await seeded_server.call_tool(
        "delete_savings", {"asset_id": asset_id}
    )
    data = extract_json(result)
    assert data["deleted"] is True
    assert data["asset_id"] == asset_id
    # Verify gone from list
    list_result = await seeded_server.call_tool("list_savings", {"active_only": False})
    list_data = extract_json(list_result)
    ids = [s["id"] for s in list_data]
    assert asset_id not in ids
    await _assert_task_deleted(seeded_server, asset_id)
