"""Tests for flux_bot.tools.budgets — LangChain tools wrapping
flux_core budget Use Cases with user_id closed over.
"""
from __future__ import annotations

from decimal import Decimal

from flux_bot.tools.budgets import build_budget_tools
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.budgets.set_budget import SetBudget


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── set_budget ───────────────────────────────────────────────────────────


async def test_set_budget_creates_row(core_db, user_id):
    tools = build_budget_tools(user_id=user_id, db=core_db)
    set_b = _tool(tools, "set_budget")

    result = await set_b.ainvoke({"category": "food", "monthly_limit": "500.00"})

    assert result["category"] == "food"
    assert result["monthly_limit"] == "500.00"
    assert "id" in result


async def test_set_budget_upserts_existing(core_db, user_id):
    """Calling set_budget twice on the same category updates the limit."""
    tools = build_budget_tools(user_id=user_id, db=core_db)
    set_b = _tool(tools, "set_budget")

    await set_b.ainvoke({"category": "transport", "monthly_limit": "100.00"})
    result = await set_b.ainvoke({"category": "transport", "monthly_limit": "200.00"})

    assert result["monthly_limit"] == "200.00"


# ── list_budgets ─────────────────────────────────────────────────────────


async def test_list_budgets_returns_seeded(core_db, user_id):
    uow = UnitOfWork(core_db)
    uc = SetBudget(uow)
    await uc.execute(user_id, "groceries", Decimal("300.00"))

    tools = build_budget_tools(user_id=user_id, db=core_db)
    lst = _tool(tools, "list_budgets")

    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["category"] == "groceries"
    assert rows[0]["monthly_limit"] == "300.00"


# ── check_budgets ────────────────────────────────────────────────────────


async def test_check_budgets_returns_list(core_db, user_id):
    uow = UnitOfWork(core_db)
    uc = SetBudget(uow)
    await uc.execute(user_id, "dining", Decimal("150.00"))

    tools = build_budget_tools(user_id=user_id, db=core_db)
    check = _tool(tools, "check_budgets")

    result = await check.ainvoke({})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["category"] == "dining"
    assert "percent_used" in result[0]
    assert "is_over_budget" in result[0]


# ── cross-user isolation ─────────────────────────────────────────────────


async def test_list_budgets_isolates_by_user(core_db, seed_user):
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    uow_a = UnitOfWork(core_db)
    await SetBudget(uow_a).execute(user_a, "cat_a", Decimal("100.00"))

    uow_b = UnitOfWork(core_db)
    await SetBudget(uow_b).execute(user_b, "cat_b", Decimal("200.00"))

    tools_a = build_budget_tools(user_id=user_a, db=core_db)
    lst = _tool(tools_a, "list_budgets")
    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["category"] == "cat_a"
    assert all(r["category"] != "cat_b" for r in rows)


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_three_named_tools(core_db, user_id):
    tools = build_budget_tools(user_id=user_id, db=core_db)
    names = {t.name for t in tools}
    assert names == {"set_budget", "list_budgets", "check_budgets"}


def test_tool_descriptions_are_non_empty(core_db, user_id):
    tools = build_budget_tools(user_id=user_id, db=core_db)
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
