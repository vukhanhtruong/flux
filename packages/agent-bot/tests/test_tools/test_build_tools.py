"""Tests for the top-level build_tools assembler.

Verifies that all domain tool builders are wired together and that each
invocation produces a distinct set of tool objects bound to the given user.
"""
from __future__ import annotations

from flux_bot.tools import build_tools


def test_build_tools_returns_all_domains(core_db, user_id, vector_store, embedding_svc):
    tools = build_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    names = {t.name for t in tools}
    must_have = {
        "add_transaction", "list_transactions", "search_transactions",
        "set_budget", "list_budgets",
        "create_goal", "list_goals",
        "save_memory", "search_memory",
        "create_subscription", "list_subscriptions",
        "create_savings",
        "get_spending_summary",
        "send_outbound_message",
    }
    missing = must_have - names
    assert not missing, f"Missing tools: {missing}"


def test_build_tools_closes_over_user_id_not_shared(
    core_db, vector_store, embedding_svc
):
    a = build_tools(
        user_id="tg:A",
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    b = build_tools(
        user_id="tg:B",
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    a_add = next(t for t in a if t.name == "add_transaction")
    b_add = next(t for t in b if t.name == "add_transaction")
    assert a_add is not b_add


def test_build_tools_all_descriptions_non_empty(
    core_db, user_id, vector_store, embedding_svc
):
    tools = build_tools(
        user_id=user_id,
        db=core_db,
        vector_store=vector_store,
        embedding_svc=embedding_svc,
    )
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name!r} has insufficient description"
        )
