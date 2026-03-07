"""E2E tests for analytics MCP tools."""
import json


def _extract_json(tool_result):
    assert len(tool_result.content) > 0
    return json.loads(tool_result.content[0].text)


async def test_generate_spending_report(seeded_server):
    """generate_spending_report parses dates and returns summary + breakdown."""
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-01",
            "amount": 50.0,
            "category": "Food",
            "description": "Groceries",
            "transaction_type": "expense",
        },
    )
    result = await seeded_server.call_tool(
        "generate_spending_report",
        {"start_date": "2026-03-01", "end_date": "2026-03-31"},
    )
    data = _extract_json(result)
    assert "total_income" in data
    assert "total_expenses" in data
    assert "category_breakdown" in data
    assert isinstance(data["category_breakdown"], list)


async def test_calculate_financial_health(seeded_server):
    """calculate_financial_health returns summary, breakdown, and period."""
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-05",
            "amount": 100.0,
            "category": "Salary",
            "description": "Pay",
            "transaction_type": "income",
        },
    )
    result = await seeded_server.call_tool(
        "calculate_financial_health",
        {"start_date": "2026-03-01", "end_date": "2026-03-31"},
    )
    data = _extract_json(result)
    assert "summary" in data
    assert "category_breakdown" in data
    assert data["period"] == {"start": "2026-03-01", "end": "2026-03-31"}
