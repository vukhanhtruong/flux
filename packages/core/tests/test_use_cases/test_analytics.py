"""Tests for analytics use cases."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from flux_core.use_cases.analytics import GetCategoryBreakdown, GetSummary, GetTrends
from flux_core.use_cases.analytics.calculate_financial_health import CalculateFinancialHealth
from flux_core.use_cases.analytics.generate_spending_report import GenerateSpendingReport

USER_ID = "tg:12345"
START = date(2026, 3, 1)
END = date(2026, 3, 31)


# ── GetSummary ──────────────────────────────────────────────────────────


async def test_get_summary():
    repo = MagicMock()
    repo.get_summary.return_value = {
        "total_income": Decimal("5000.00"),
        "total_expenses": Decimal("3200.00"),
        "count": 42,
    }

    uc = GetSummary(repo)
    result = await uc.execute(USER_ID, START, END)

    assert result["total_income"] == "5000.00"
    assert result["total_expenses"] == "3200.00"
    assert result["net"] == "1800.00"
    assert result["count"] == 42
    repo.get_summary.assert_called_once_with(USER_ID, START, END)


async def test_get_summary_no_data():
    repo = MagicMock()
    repo.get_summary.return_value = {
        "total_income": None,
        "total_expenses": None,
        "count": 0,
    }

    uc = GetSummary(repo)
    result = await uc.execute(USER_ID, START, END)

    assert result["total_income"] == "0"
    assert result["total_expenses"] == "0"
    assert result["net"] == "0"


# ── GetTrends ───────────────────────────────────────────────────────────


async def test_get_trends():
    repo = MagicMock()
    repo.get_summary.side_effect = [
        # current period
        {"total_expenses": Decimal("3000.00"), "total_income": Decimal("5000.00")},
        # previous period
        {"total_expenses": Decimal("2500.00"), "total_income": Decimal("4500.00")},
    ]

    uc = GetTrends(repo)
    prev_start = date(2026, 2, 1)
    prev_end = date(2026, 2, 28)
    result = await uc.execute(USER_ID, START, END, prev_start, prev_end)

    assert result["current_expenses"] == "3000.00"
    assert result["previous_expenses"] == "2500.00"
    assert result["expense_change"] == "500.00"
    assert result["expense_change_pct"] == "20.00"
    assert result["income_change"] == "500.00"


async def test_get_trends_no_previous():
    repo = MagicMock()
    repo.get_summary.side_effect = [
        {"total_expenses": Decimal("3000.00"), "total_income": Decimal("5000.00")},
        {"total_expenses": None, "total_income": None},
    ]

    uc = GetTrends(repo)
    result = await uc.execute(
        USER_ID, START, END, date(2026, 2, 1), date(2026, 2, 28)
    )

    assert result["expense_change_pct"] == "0"
    assert result["income_change_pct"] == "0"


# ── GetCategoryBreakdown ────────────────────────────────────────────────


async def test_get_category_breakdown():
    repo = MagicMock()
    repo.get_category_breakdown.return_value = [
        {"category": "food", "total": Decimal("1200.00"), "count": 15},
        {"category": "transport", "total": Decimal("500.00"), "count": 8},
    ]

    uc = GetCategoryBreakdown(repo)
    result = await uc.execute(USER_ID, START, END)

    assert len(result) == 2
    assert result[0]["category"] == "food"
    assert result[0]["total"] == "1200.00"
    assert result[1]["count"] == 8
    repo.get_category_breakdown.assert_called_once_with(USER_ID, START, END)


async def test_get_category_breakdown_empty():
    repo = MagicMock()
    repo.get_category_breakdown.return_value = []

    uc = GetCategoryBreakdown(repo)
    result = await uc.execute(USER_ID, START, END)

    assert result == []


# ── GenerateSpendingReport ────────────────────────────────────────────


async def test_generate_spending_report():
    repo = MagicMock()
    repo.get_summary.return_value = {
        "total_income": Decimal("5000"),
        "total_expenses": Decimal("3000"),
        "net": Decimal("2000"),
        "count": 25,
    }
    repo.get_category_breakdown.return_value = [
        {"category": "food", "total": Decimal("1000")}
    ]

    uc = GenerateSpendingReport(repo)
    result = await uc.execute("u1", date(2024, 1, 1), date(2024, 1, 31))

    assert result["total_income"] == Decimal("5000")
    assert "category_breakdown" in result
    assert len(result["category_breakdown"]) == 1


# ── CalculateFinancialHealth ──────────────────────────────────────────


async def test_calculate_financial_health():
    repo = MagicMock()
    repo.get_summary.return_value = {
        "total_income": Decimal("5000"),
        "total_expenses": Decimal("3000"),
    }

    uc = CalculateFinancialHealth(repo)
    result = await uc.execute("u1", date(2024, 1, 1), date(2024, 1, 31))

    assert result["score"] == 40
    assert result["savings_rate"] == 0.4
    assert "budget_adherence" in result
    assert "goal_progress" in result


async def test_financial_health_zero_income():
    repo = MagicMock()
    repo.get_summary.return_value = {
        "total_income": Decimal("0"),
        "total_expenses": Decimal("100"),
    }

    uc = CalculateFinancialHealth(repo)
    result = await uc.execute("u1", date(2024, 1, 1), date(2024, 1, 31))

    assert result["score"] == 0
    assert result["savings_rate"] == 0.0
