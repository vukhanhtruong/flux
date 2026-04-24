"""Tests for flux_bot.tools.savings — LangChain tools wrapping
flux_core savings Use Cases with user_id closed over.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from flux_bot.tools.savings import build_savings_tools
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.savings.create_savings import CreateSavings


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── create_savings ───────────────────────────────────────────────────────


async def test_create_savings_creates_row(core_db, user_id):
    tools = build_savings_tools(user_id=user_id, db=core_db)
    create = _tool(tools, "create_savings")

    result = await create.ainvoke(
        {
            "name": "Fixed Deposit",
            "amount": "10000.00",
            "interest_rate": "5.0",
            "compound_frequency": "at_maturity",
            "start_date": "2026-04-01",
            "maturity_date": "2027-04-01",
            "category": "savings",
        }
    )

    assert result["name"] == "Fixed Deposit"
    assert result["amount"] == "10000.00"
    assert result["active"] is True
    assert "id" in result
    assert result["maturity_date"] == "2027-04-01"


async def test_create_savings_monthly_compound(core_db, user_id):
    tools = build_savings_tools(user_id=user_id, db=core_db)
    create = _tool(tools, "create_savings")

    result = await create.ainvoke(
        {
            "name": "Monthly Savings",
            "amount": "5000.00",
            "interest_rate": "3.5",
            "compound_frequency": "monthly",
            "start_date": "2026-01-01",
            "maturity_date": "2027-01-01",
            "category": "savings",
        }
    )

    assert result["active"] is True
    assert result["compound_frequency"] == "monthly"


# ── withdraw_savings ─────────────────────────────────────────────────────


async def test_withdraw_savings_returns_transaction(core_db, user_id):
    """Create a savings deposit then withdraw it — should create an income txn."""
    uow = UnitOfWork(core_db)
    asset = await CreateSavings(uow).execute(
        user_id=user_id,
        name="Test FD",
        amount=Decimal("2000.00"),
        interest_rate=Decimal("4.0"),
        compound_frequency="at_maturity",
        start_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        category="savings",
    )

    tools = build_savings_tools(user_id=user_id, db=core_db)
    withdraw = _tool(tools, "withdraw_savings")

    result = await withdraw.ainvoke({"asset_id": str(asset.id)})

    assert "withdrawn_amount" in result
    assert Decimal(result["withdrawn_amount"]) == Decimal("2000.00")
    assert "transaction_id" in result
    assert result["asset_name"] == "Test FD"


async def test_withdraw_nonexistent_savings_raises(core_db, user_id):
    tools = build_savings_tools(user_id=user_id, db=core_db)
    withdraw = _tool(tools, "withdraw_savings")

    import pytest
    with pytest.raises(Exception):
        await withdraw.ainvoke({"asset_id": "00000000-0000-0000-0000-000000000000"})


# ── surface sanity ───────────────────────────────────────────────────────


async def test_withdraw_isolates_by_user(core_db, seed_user):
    """User B cannot withdraw a savings account that belongs to user A."""
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    uow = UnitOfWork(core_db)
    asset_a = await CreateSavings(uow).execute(
        user_id=user_a,
        name="Alice's FD",
        amount=Decimal("1000.00"),
        interest_rate=Decimal("5.0"),
        compound_frequency="at_maturity",
        start_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        category="savings",
    )

    tools_b = build_savings_tools(user_id=user_b, db=core_db)
    withdraw = _tool(tools_b, "withdraw_savings")

    import pytest
    with pytest.raises(Exception):
        # WithdrawSavings raises ValueError when asset_repo.get(asset_id, user_b) → None
        await withdraw.ainvoke({"asset_id": str(asset_a.id)})


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_two_named_tools(core_db, user_id):
    tools = build_savings_tools(user_id=user_id, db=core_db)
    names = {t.name for t in tools}
    assert names == {"create_savings", "withdraw_savings"}


def test_tool_descriptions_are_non_empty(core_db, user_id):
    tools = build_savings_tools(user_id=user_id, db=core_db)
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
