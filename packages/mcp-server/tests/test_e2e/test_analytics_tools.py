"""E2E tests for analytics MCP tools."""
from .conftest import extract_json


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
    data = extract_json(result)
    assert "total_income" in data
    assert "total_expenses" in data
    assert "category_breakdown" in data
    assert isinstance(data["category_breakdown"], list)


async def test_calculate_financial_health(seeded_server):
    """calculate_financial_health returns score, savings_rate, budget/goal progress."""
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
    data = extract_json(result)
    assert "score" in data
    assert "savings_rate" in data
    assert "budget_adherence" in data
    assert "goal_progress" in data


async def test_get_trends(seeded_server):
    """get_trends compares two periods and returns expense/income changes."""
    # Add transactions in the "current" period (March 2026)
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-05",
            "amount": 80.0,
            "category": "Food",
            "description": "March groceries",
            "transaction_type": "expense",
        },
    )
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-03-10",
            "amount": 200.0,
            "category": "Salary",
            "description": "March pay",
            "transaction_type": "income",
        },
    )
    # Add transactions in the "previous" period (February 2026)
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-02-05",
            "amount": 60.0,
            "category": "Food",
            "description": "Feb groceries",
            "transaction_type": "expense",
        },
    )
    await seeded_server.call_tool(
        "add_transaction",
        {
            "date": "2026-02-10",
            "amount": 150.0,
            "category": "Salary",
            "description": "Feb pay",
            "transaction_type": "income",
        },
    )

    result = await seeded_server.call_tool(
        "get_trends",
        {
            "current_start": "2026-03-01",
            "current_end": "2026-03-31",
            "previous_start": "2026-02-01",
            "previous_end": "2026-02-28",
        },
    )
    data = extract_json(result)

    assert "current_expenses" in data
    assert "previous_expenses" in data
    assert "expense_change" in data
    assert "expense_change_pct" in data
    assert "current_income" in data
    assert "previous_income" in data
    assert "income_change" in data
    assert "income_change_pct" in data
