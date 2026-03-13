"""E2E tests for transaction MCP tools — edge cases."""
from datetime import datetime
from zoneinfo import ZoneInfo

from .conftest import extract_json


async def test_add_transaction_date_today(seeded_server):
    """add_transaction with date='today' resolves to today in user timezone."""
    result = await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "today",
            "amount": 25.0,
            "category": "Food",
            "description": "Lunch",
            "transaction_type": "expense",
        },
    )
    data = extract_json(result)
    expected_date = datetime.now(ZoneInfo("UTC")).date().isoformat()
    assert data["date"] == expected_date


async def test_search_transactions_response_format(seeded_server):
    """search_transactions response excludes is_recurring and tags."""
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-01",
            "amount": 50.0,
            "category": "Food",
            "description": "Searchable lunch",
            "transaction_type": "expense",
            "tags": ["lunch", "work"],
        },
    )
    result = await seeded_server.call_tool(
        "search_transactions", {"query": "lunch", "limit": 5}
    )
    data = extract_json(result)
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "id" in item
        assert "date" in item
        assert "amount" in item
        assert "category" in item
        assert "description" in item
        assert "type" in item
        assert "is_recurring" not in item
        assert "tags" not in item


async def test_delete_transaction(seeded_server):
    """delete_transaction removes a transaction and returns success."""
    # Create a transaction first
    add_result = await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-01",
            "amount": 30.0,
            "category": "Food",
            "description": "To be deleted",
            "transaction_type": "expense",
        },
    )
    txn = extract_json(add_result)
    txn_id = txn["id"]

    # Delete it
    del_result = await seeded_server.call_tool(
        "delete_transaction", {"transaction_id": txn_id}
    )
    data = extract_json(del_result)
    assert data["deleted"] is True

    # Verify it's gone from list
    list_result = await seeded_server.call_tool(
        "list_transactions", {"limit": 100}
    )
    listed = extract_json(list_result)
    assert all(t["id"] != txn_id for t in listed)


async def test_delete_transaction_not_found(seeded_server):
    """delete_transaction returns deleted=false for nonexistent ID."""
    result = await seeded_server.call_tool(
        "delete_transaction",
        {"transaction_id": "00000000-0000-0000-0000-000000000000"},
    )
    data = extract_json(result)
    assert data["deleted"] is False


async def test_update_transaction(seeded_server):
    """update_transaction modifies fields and returns updated transaction."""
    # Create a transaction first
    add_result = await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-01",
            "amount": 20.0,
            "category": "Food",
            "description": "Original lunch",
            "transaction_type": "expense",
        },
    )
    txn = extract_json(add_result)
    txn_id = txn["id"]

    # Update it
    upd_result = await seeded_server.call_tool(
        "update_transaction",
        {
            "transaction_id": txn_id,
            "category": "Dining",
            "amount": 25.0,
            "description": "Updated lunch",
        },
    )
    data = extract_json(upd_result)
    assert data["id"] == txn_id
    assert data["category"] == "Dining"
    assert float(data["amount"]) == 25.0
    assert data["description"] == "Updated lunch"


async def test_update_transaction_not_found(seeded_server):
    """update_transaction raises error for nonexistent ID."""
    import pytest

    with pytest.raises(Exception, match="not found"):
        await seeded_server.call_tool(
            "update_transaction",
            {
                "transaction_id": "00000000-0000-0000-0000-000000000000",
                "category": "Nope",
            },
        )
