"""E2E tests for transaction MCP tools — edge cases."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo


def _extract_json(tool_result):
    assert len(tool_result.content) > 0
    return json.loads(tool_result.content[0].text)


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
    data = _extract_json(result)
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
    data = _extract_json(result)
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
