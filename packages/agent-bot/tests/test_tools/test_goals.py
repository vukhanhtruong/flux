"""Tests for flux_bot.tools.goals — LangChain tools wrapping
flux_core goal Use Cases with user_id closed over.
"""
from __future__ import annotations

from decimal import Decimal

from flux_bot.tools.goals import build_goal_tools
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.goals.create_goal import CreateGoal


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── create_goal ──────────────────────────────────────────────────────────


async def test_create_goal_creates_row(core_db, user_id):
    tools = build_goal_tools(user_id=user_id, db=core_db)
    create = _tool(tools, "create_goal")

    result = await create.ainvoke(
        {"name": "Vacation Fund", "target_amount": "3000.00"}
    )

    assert result["name"] == "Vacation Fund"
    assert result["target_amount"] == "3000.00"
    assert Decimal(result["current_amount"]) == Decimal("0")
    assert "id" in result


async def test_create_goal_with_deadline(core_db, user_id):
    tools = build_goal_tools(user_id=user_id, db=core_db)
    create = _tool(tools, "create_goal")

    result = await create.ainvoke(
        {
            "name": "Emergency Fund",
            "target_amount": "5000.00",
            "deadline": "2027-01-01",
            "color": "#FF0000",
        }
    )

    assert result["deadline"] == "2027-01-01"
    assert result["color"] == "#FF0000"


# ── list_goals ───────────────────────────────────────────────────────────


async def test_list_goals_returns_seeded(core_db, user_id):
    uow = UnitOfWork(core_db)
    uc = CreateGoal(uow)
    await uc.execute(user_id, "New Car", Decimal("20000.00"))

    tools = build_goal_tools(user_id=user_id, db=core_db)
    lst = _tool(tools, "list_goals")

    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["name"] == "New Car"
    assert rows[0]["target_amount"] == "20000.00"


# ── deposit_to_goal ──────────────────────────────────────────────────────


async def test_deposit_to_goal_increases_amount(core_db, user_id):
    uow = UnitOfWork(core_db)
    goal = await CreateGoal(uow).execute(user_id, "Laptop", Decimal("1500.00"))

    tools = build_goal_tools(user_id=user_id, db=core_db)
    deposit = _tool(tools, "deposit_to_goal")

    result = await deposit.ainvoke({"goal_id": str(goal.id), "amount": "200.00"})

    assert Decimal(result["current_amount"]) == Decimal("200.00")
    assert result["name"] == "Laptop"


async def test_deposit_to_nonexistent_goal_returns_error(core_db, user_id):
    tools = build_goal_tools(user_id=user_id, db=core_db)
    deposit = _tool(tools, "deposit_to_goal")

    result = await deposit.ainvoke(
        {"goal_id": "00000000-0000-0000-0000-000000000000", "amount": "100.00"}
    )

    assert "error" in result


# ── withdraw_from_goal ───────────────────────────────────────────────────


async def test_withdraw_from_goal(core_db, user_id):
    uow = UnitOfWork(core_db)
    goal = await CreateGoal(uow).execute(user_id, "Savings", Decimal("1000.00"))
    uow2 = UnitOfWork(core_db)
    from flux_core.use_cases.goals.deposit_to_goal import DepositToGoal

    await DepositToGoal(uow2).execute(goal.id, user_id, Decimal("500.00"))

    tools = build_goal_tools(user_id=user_id, db=core_db)
    withdraw = _tool(tools, "withdraw_from_goal")

    result = await withdraw.ainvoke({"goal_id": str(goal.id), "amount": "100.00"})

    assert Decimal(result["current_amount"]) == Decimal("400.00")


# ── delete_goal ──────────────────────────────────────────────────────────


async def test_delete_goal_removes_row(core_db, user_id):
    uow = UnitOfWork(core_db)
    goal = await CreateGoal(uow).execute(user_id, "Temp Goal", Decimal("500.00"))

    tools = build_goal_tools(user_id=user_id, db=core_db)
    delete = _tool(tools, "delete_goal")
    lst = _tool(tools, "list_goals")

    result = await delete.ainvoke({"goal_id": str(goal.id)})
    rows = await lst.ainvoke({})

    assert result["deleted"] is True
    assert len(rows) == 0


# ── cross-user isolation ─────────────────────────────────────────────────


async def test_list_goals_isolates_by_user(core_db, seed_user):
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    uow_a = UnitOfWork(core_db)
    await CreateGoal(uow_a).execute(user_a, "Alice Goal", Decimal("100.00"))

    uow_b = UnitOfWork(core_db)
    await CreateGoal(uow_b).execute(user_b, "Bob Goal", Decimal("200.00"))

    tools_a = build_goal_tools(user_id=user_a, db=core_db)
    lst = _tool(tools_a, "list_goals")
    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["name"] == "Alice Goal"
    assert all(r["name"] != "Bob Goal" for r in rows)


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_five_named_tools(core_db, user_id):
    tools = build_goal_tools(user_id=user_id, db=core_db)
    names = {t.name for t in tools}
    assert names == {
        "create_goal",
        "list_goals",
        "deposit_to_goal",
        "withdraw_from_goal",
        "delete_goal",
    }


def test_tool_descriptions_are_non_empty(core_db, user_id):
    tools = build_goal_tools(user_id=user_id, db=core_db)
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
