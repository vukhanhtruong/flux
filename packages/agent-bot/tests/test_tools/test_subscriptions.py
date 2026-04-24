"""Tests for flux_bot.tools.subscriptions — LangChain tools wrapping
flux_core subscription Use Cases with user_id closed over.
"""
from __future__ import annotations

from decimal import Decimal

from flux_bot.tools.subscriptions import build_subscription_tools
from flux_core.models.subscription import BillingCycle
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.subscriptions.create_subscription import CreateSubscription


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── create_subscription ──────────────────────────────────────────────────


async def test_create_subscription_creates_row(core_db, user_id):
    tools = build_subscription_tools(user_id=user_id, db=core_db)
    create = _tool(tools, "create_subscription")

    result = await create.ainvoke(
        {
            "name": "Spotify",
            "amount": "9.99",
            "billing_cycle": "monthly",
            "next_date": "2026-05-01",
            "category": "entertainment",
        }
    )

    assert result["name"] == "Spotify"
    assert result["amount"] == "9.99"
    assert result["billing_cycle"] == "monthly"
    assert result["active"] is True
    assert "id" in result


# ── list_subscriptions ───────────────────────────────────────────────────


async def test_list_subscriptions_returns_seeded(core_db, user_id):
    uow = UnitOfWork(core_db)
    uc = CreateSubscription(uow)
    from datetime import date

    await uc.execute(
        user_id, "Netflix", Decimal("15.99"), BillingCycle.monthly,
        date(2026, 5, 1), "entertainment"
    )

    tools = build_subscription_tools(user_id=user_id, db=core_db)
    lst = _tool(tools, "list_subscriptions")

    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["name"] == "Netflix"
    assert rows[0]["billing_cycle"] == "monthly"


async def test_list_subscriptions_active_only(core_db, user_id):
    from datetime import date

    uow = UnitOfWork(core_db)
    uc = CreateSubscription(uow)
    sub = await uc.execute(
        user_id, "Adobe", Decimal("54.99"), BillingCycle.monthly,
        date(2026, 5, 1), "software"
    )

    # Toggle to inactive
    uow2 = UnitOfWork(core_db)
    from flux_core.use_cases.subscriptions.toggle_subscription import ToggleSubscription

    await ToggleSubscription(uow2).execute(sub.id, user_id)

    tools = build_subscription_tools(user_id=user_id, db=core_db)
    lst = _tool(tools, "list_subscriptions")

    active_rows = await lst.ainvoke({"active_only": True})
    all_rows = await lst.ainvoke({"active_only": False})

    assert len(active_rows) == 0
    assert len(all_rows) == 1


# ── toggle_subscription ──────────────────────────────────────────────────


async def test_toggle_subscription_deactivates(core_db, user_id):
    from datetime import date

    uow = UnitOfWork(core_db)
    sub = await CreateSubscription(uow).execute(
        user_id, "iCloud", Decimal("2.99"), BillingCycle.monthly,
        date(2026, 5, 1), "storage"
    )

    tools = build_subscription_tools(user_id=user_id, db=core_db)
    toggle = _tool(tools, "toggle_subscription")

    result = await toggle.ainvoke({"subscription_id": str(sub.id)})

    assert result["active"] is False
    assert result["id"] == str(sub.id)


# ── delete_subscription ──────────────────────────────────────────────────


async def test_delete_subscription_removes_row(core_db, user_id):
    from datetime import date

    uow = UnitOfWork(core_db)
    sub = await CreateSubscription(uow).execute(
        user_id, "Temp Sub", Decimal("1.00"), BillingCycle.monthly,
        date(2026, 5, 1), "misc"
    )

    tools = build_subscription_tools(user_id=user_id, db=core_db)
    delete = _tool(tools, "delete_subscription")
    lst = _tool(tools, "list_subscriptions")

    result = await delete.ainvoke({"subscription_id": str(sub.id)})
    rows = await lst.ainvoke({"active_only": False})

    assert result["deleted"] is True
    assert len(rows) == 0


# ── cross-user isolation ─────────────────────────────────────────────────


async def test_list_subscriptions_isolates_by_user(core_db, seed_user):
    from datetime import date

    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    uow_a = UnitOfWork(core_db)
    await CreateSubscription(uow_a).execute(
        user_a, "Alice Sub", Decimal("10.00"), BillingCycle.monthly,
        date(2026, 5, 1), "cat_a"
    )

    uow_b = UnitOfWork(core_db)
    await CreateSubscription(uow_b).execute(
        user_b, "Bob Sub", Decimal("20.00"), BillingCycle.monthly,
        date(2026, 5, 1), "cat_b"
    )

    tools_a = build_subscription_tools(user_id=user_a, db=core_db)
    lst = _tool(tools_a, "list_subscriptions")
    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["name"] == "Alice Sub"
    assert all(r["name"] != "Bob Sub" for r in rows)


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_four_named_tools(core_db, user_id):
    tools = build_subscription_tools(user_id=user_id, db=core_db)
    names = {t.name for t in tools}
    assert names == {
        "create_subscription",
        "list_subscriptions",
        "toggle_subscription",
        "delete_subscription",
    }


def test_tool_descriptions_are_non_empty(core_db, user_id):
    tools = build_subscription_tools(user_id=user_id, db=core_db)
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
