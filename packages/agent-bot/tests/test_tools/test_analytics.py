"""Tests for flux_bot.tools.analytics — LangChain tools wrapping
flux_core analytics Use Cases with user_id closed over.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from flux_bot.tools.analytics import build_analytics_tools
from flux_core.models.transaction import TransactionType
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.transactions.add_transaction import AddTransaction


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── get_spending_summary ─────────────────────────────────────────────────


async def test_get_spending_summary_returns_without_error(core_db, user_id):
    tools = build_analytics_tools(user_id=user_id, db=core_db)
    summary = _tool(tools, "get_spending_summary")

    result = await summary.ainvoke(
        {"start_date": "2026-04-01", "end_date": "2026-04-30"}
    )

    assert "total_expenses" in result
    assert "total_income" in result
    assert "net" in result
    assert "count" in result


async def test_get_spending_summary_reflects_seeded_data(
    core_db, user_id, vector_store, embedding_svc
):
    uow = UnitOfWork(core_db)
    uc = AddTransaction(uow, embedding_svc)
    await uc.execute(
        user_id=user_id,
        date=date(2026, 4, 10),
        amount=Decimal("100.00"),
        category="food",
        description="groceries",
        transaction_type=TransactionType.expense,
    )

    tools = build_analytics_tools(user_id=user_id, db=core_db)
    summary = _tool(tools, "get_spending_summary")

    result = await summary.ainvoke(
        {"start_date": "2026-04-01", "end_date": "2026-04-30"}
    )

    assert Decimal(result["total_expenses"]) == Decimal("100.00")
    assert result["count"] == 1


# ── get_category_breakdown ───────────────────────────────────────────────


async def test_get_category_breakdown_on_seeded_data(
    core_db, user_id, vector_store, embedding_svc
):
    uow = UnitOfWork(core_db)
    uc = AddTransaction(uow, embedding_svc)
    await uc.execute(
        user_id=user_id,
        date=date(2026, 4, 5),
        amount=Decimal("50.00"),
        category="transport",
        description="bus pass",
        transaction_type=TransactionType.expense,
    )

    tools = build_analytics_tools(user_id=user_id, db=core_db)
    breakdown = _tool(tools, "get_category_breakdown")

    result = await breakdown.ainvoke(
        {"start_date": "2026-04-01", "end_date": "2026-04-30"}
    )

    assert isinstance(result, list)
    categories = {r["category"] for r in result}
    assert "transport" in categories
    transport_row = next(r for r in result if r["category"] == "transport")
    assert Decimal(transport_row["total"]) == Decimal("50.00")


async def test_get_category_breakdown_empty_returns_list(core_db, user_id):
    tools = build_analytics_tools(user_id=user_id, db=core_db)
    breakdown = _tool(tools, "get_category_breakdown")

    result = await breakdown.ainvoke(
        {"start_date": "2020-01-01", "end_date": "2020-01-31"}
    )

    assert isinstance(result, list)
    assert len(result) == 0


# ── get_trends ───────────────────────────────────────────────────────────


async def test_get_trends_returns_comparison_dict(core_db, user_id):
    tools = build_analytics_tools(user_id=user_id, db=core_db)
    trends = _tool(tools, "get_trends")

    result = await trends.ainvoke(
        {
            "current_start": "2026-04-01",
            "current_end": "2026-04-30",
            "previous_start": "2026-03-01",
            "previous_end": "2026-03-31",
        }
    )

    assert "current_expenses" in result
    assert "previous_expenses" in result
    assert "expense_change" in result
    assert "expense_change_pct" in result


# ── cross-user isolation ─────────────────────────────────────────────────


async def test_spending_summary_isolates_by_user(core_db, seed_user, vector_store, embedding_svc):
    """User B's summary returns zero even when user A has transactions."""
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    uow_a = UnitOfWork(core_db)
    await AddTransaction(uow_a, embedding_svc).execute(
        user_id=user_a,
        date=date(2026, 4, 10),
        amount=Decimal("200.00"),
        category="food",
        description="Alice groceries",
        transaction_type=TransactionType.expense,
    )

    tools_b = build_analytics_tools(user_id=user_b, db=core_db)
    summary = _tool(tools_b, "get_spending_summary")
    result = await summary.ainvoke({"start_date": "2026-04-01", "end_date": "2026-04-30"})

    assert Decimal(result["total_expenses"]) == Decimal("0"), (
        "User B should see zero expenses, not user A's data"
    )


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_three_named_tools(core_db, user_id):
    tools = build_analytics_tools(user_id=user_id, db=core_db)
    names = {t.name for t in tools}
    assert names == {"get_spending_summary", "get_category_breakdown", "get_trends"}


def test_tool_descriptions_are_non_empty(core_db, user_id):
    tools = build_analytics_tools(user_id=user_id, db=core_db)
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
