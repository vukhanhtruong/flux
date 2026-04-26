"""Tests for flux_bot.tools.transactions — LangChain tools wrapping
flux_core transaction Use Cases with user_id closed over.

The core property under test: tools bound to user A can never observe
user B's data, because user_id is captured at build time and never
exposed as a tool argument.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from flux_bot.tools.transactions import build_transaction_tools
from flux_core.models.transaction import TransactionType
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.transactions.add_transaction import AddTransaction


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── add_transaction ─────────────────────────────────────────────────────


async def test_add_transaction_creates_row(core_db, user_id, vector_store, embedding_svc):
    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    add = _tool(tools, "add_transaction")

    result = await add.ainvoke(
        {
            "date": "2026-04-23",
            "amount": "12.50",
            "category": "coffee",
            "description": "morning latte",
            "transaction_type": "expense",
        }
    )

    assert "id" in result
    assert result["amount"] == "12.50"
    assert result["category"] == "coffee"
    assert result["type"] == "expense"


async def test_add_transaction_accepts_today(core_db, user_id, vector_store, embedding_svc):
    """'today' is a special sentinel the MCP surface accepts — mirror it."""
    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    add = _tool(tools, "add_transaction")

    result = await add.ainvoke(
        {
            "date": "today",
            "amount": "5.00",
            "category": "snack",
            "description": "candy",
            "transaction_type": "expense",
        }
    )

    assert "id" in result
    # The exact date is tz-sensitive; just assert it's a valid ISO date.
    assert date.fromisoformat(result["date"])


# ── list_transactions ───────────────────────────────────────────────────


async def test_list_transactions_returns_seeded_rows(
    core_db, user_id, vector_store, embedding_svc
):
    # Seed via the real Use Case so the data shape matches production.
    uow = UnitOfWork(core_db)
    uc = AddTransaction(uow, embedding_svc)
    await uc.execute(
        user_id=user_id,
        date=date(2026, 4, 1),
        amount=Decimal("9.99"),
        category="food",
        description="breakfast",
        transaction_type=TransactionType.expense,
    )

    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    lst = _tool(tools, "list_transactions")

    rows = await lst.ainvoke({"limit": 50})

    assert len(rows) == 1
    assert rows[0]["category"] == "food"
    assert rows[0]["amount"] == "9.99"


# ── search_transactions ─────────────────────────────────────────────────


async def test_search_transactions_returns_seeded_match(
    core_db, user_id, vector_store, embedding_svc
):
    uow = UnitOfWork(core_db)
    uc = AddTransaction(uow, embedding_svc)
    await uc.execute(
        user_id=user_id,
        date=date(2026, 4, 2),
        amount=Decimal("42.00"),
        category="dining",
        description="sushi dinner",
        transaction_type=TransactionType.expense,
    )

    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    search = _tool(tools, "search_transactions")

    # The fake embedding is deterministic and hash-based, so "dining sushi
    # dinner" and "dining sushi dinner" produce identical vectors — we
    # query with the same phrase the row was embedded with to guarantee
    # a hit regardless of fake-embedding distance semantics.
    rows = await search.ainvoke({"query": "dining sushi dinner", "limit": 5})

    assert len(rows) >= 1
    assert any(r["category"] == "dining" for r in rows)


# ── cross-user isolation (the load-bearing test) ────────────────────────


async def test_list_isolates_by_closed_over_user_id(
    core_db, vector_store, embedding_svc, seed_user
):
    """A tool built for user A must never see user B's rows, even when
    both users coexist in the same database."""
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    # Seed one transaction per user via the real Use Case.
    uow = UnitOfWork(core_db)
    uc = AddTransaction(uow, embedding_svc)
    await uc.execute(
        user_id=user_a,
        date=date(2026, 4, 3),
        amount=Decimal("1.00"),
        category="alice_cat",
        description="alice txn",
        transaction_type=TransactionType.expense,
    )
    await uc.execute(
        user_id=user_b,
        date=date(2026, 4, 3),
        amount=Decimal("2.00"),
        category="bob_cat",
        description="bob txn",
        transaction_type=TransactionType.expense,
    )

    alice_tools = build_transaction_tools(
        user_id=user_a,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    lst = _tool(alice_tools, "list_transactions")
    rows = await lst.ainvoke({"limit": 50})

    assert len(rows) == 1
    assert rows[0]["category"] == "alice_cat"
    categories = {r["category"] for r in rows}
    assert "bob_cat" not in categories


# ── surface sanity ──────────────────────────────────────────────────────


def test_build_returns_three_named_tools(core_db, user_id, vector_store, embedding_svc):
    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    names = {t.name for t in tools}
    assert names == {"add_transaction", "list_transactions", "search_transactions"}


def test_tool_descriptions_are_non_empty(core_db, user_id, vector_store, embedding_svc):
    """Docstrings become the model-facing description — must be non-trivial."""
    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )


def test_different_user_ids_yield_distinct_tool_instances(
    core_db, vector_store, embedding_svc
):
    a = build_transaction_tools(
        user_id="tg:a", db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    b = build_transaction_tools(
        user_id="tg:b", db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    a_add = _tool(a, "add_transaction")
    b_add = _tool(b, "add_transaction")
    assert a_add is not b_add


async def test_build_uses_default_embedding_svc_when_omitted(
    core_db, user_id, vector_store, monkeypatch
):
    """When no embedding_svc is passed, the module falls back to a
    lazily-constructed process-level ``EmbeddingService``. Patch the
    constructor so we don't trigger the fastembed model download."""
    from flux_bot.tools import transactions as tools_mod

    # Reset the module-level singleton so the lazy path is taken.
    monkeypatch.setattr(tools_mod, "_default_embedding_svc", None)

    calls: list[str] = []

    class _StubEmbeddingService:
        def __init__(self, *args, **kwargs):
            calls.append("constructed")

        def embed(self, text: str) -> list[float]:
            return [0.0] * 384

    monkeypatch.setattr(
        "flux_core.embeddings.service.EmbeddingService",
        _StubEmbeddingService,
    )

    tools = build_transaction_tools(
        user_id=user_id, db=core_db, vector_store=vector_store
    )
    add = _tool(tools, "add_transaction")
    await add.ainvoke(
        {
            "date": "2026-04-23",
            "amount": "1.00",
            "category": "c",
            "description": "d",
            "transaction_type": "expense",
        }
    )

    assert calls == ["constructed"]
    # Reset again so later tests don't see our stub cached.
    monkeypatch.setattr(tools_mod, "_default_embedding_svc", None)


@pytest.mark.parametrize(
    "bad_type",
    ["transfer", "EXPENSE", "", "foo"],
)
async def test_add_transaction_rejects_unknown_type(
    core_db, user_id, vector_store, embedding_svc, bad_type
):
    tools = build_transaction_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    add = _tool(tools, "add_transaction")

    with pytest.raises(Exception):
        await add.ainvoke(
            {
                "date": "2026-04-23",
                "amount": "1.00",
                "category": "c",
                "description": "d",
                "transaction_type": bad_type,
            }
        )
