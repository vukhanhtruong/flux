"""Tests for flux_bot.tools.memory — LangChain tools wrapping
flux_core memory Use Cases with user_id closed over.
"""
from __future__ import annotations

from flux_bot.tools.memory import build_memory_tools
from flux_core.models.memory import MemoryType
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.memory.remember import Remember


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── save_memory ──────────────────────────────────────────────────────────


async def test_save_memory_creates_row(core_db, user_id, vector_store, embedding_svc):
    tools = build_memory_tools(
        user_id=user_id, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    save = _tool(tools, "save_memory")

    result = await save.ainvoke(
        {"memory_type": "fact", "content": "User prefers dark mode."}
    )

    assert "id" in result
    assert result["memory_type"] == "fact"
    assert result["content"] == "User prefers dark mode."


# ── list_memories ────────────────────────────────────────────────────────


async def test_list_memories_returns_seeded(core_db, user_id, vector_store, embedding_svc):
    uow = UnitOfWork(core_db, vector_store=vector_store)
    uc = Remember(uow, embedding_svc)
    await uc.execute(user_id, MemoryType.preference, "User likes summaries.")

    tools = build_memory_tools(
        user_id=user_id, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    lst = _tool(tools, "list_memories")

    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["memory_type"] == "preference"
    assert rows[0]["content"] == "User likes summaries."
    assert "created_at" in rows[0]


async def test_list_memories_filter_by_type(core_db, user_id, vector_store, embedding_svc):
    uow = UnitOfWork(core_db, vector_store=vector_store)
    uc = Remember(uow, embedding_svc)
    await uc.execute(user_id, MemoryType.fact, "Fact memory.")
    uow2 = UnitOfWork(core_db, vector_store=vector_store)
    await Remember(uow2, embedding_svc).execute(user_id, MemoryType.preference, "Pref memory.")

    tools = build_memory_tools(
        user_id=user_id, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    lst = _tool(tools, "list_memories")

    rows = await lst.ainvoke({"memory_type": "fact"})

    assert len(rows) == 1
    assert rows[0]["memory_type"] == "fact"


# ── search_memory ────────────────────────────────────────────────────────


async def test_search_memory_returns_saved_item(core_db, user_id, vector_store, embedding_svc):
    uow = UnitOfWork(core_db, vector_store=vector_store)
    uc = Remember(uow, embedding_svc)
    await uc.execute(user_id, MemoryType.fact, "dark mode preferred")

    tools = build_memory_tools(
        user_id=user_id, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    search = _tool(tools, "search_memory")

    result = await search.ainvoke({"query": "dark mode preferred", "limit": 5})

    assert "memories" in result
    assert len(result["memories"]) >= 1
    assert any("dark mode" in m["content"] for m in result["memories"])


# ── cross-user isolation ─────────────────────────────────────────────────


async def test_list_memories_isolates_by_user(
    core_db, vector_store, embedding_svc, seed_user
):
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    uow_a = UnitOfWork(core_db, vector_store=vector_store)
    await Remember(uow_a, embedding_svc).execute(user_a, MemoryType.fact, "Alice fact")

    uow_b = UnitOfWork(core_db, vector_store=vector_store)
    await Remember(uow_b, embedding_svc).execute(user_b, MemoryType.fact, "Bob fact")

    tools_a = build_memory_tools(
        user_id=user_a, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    lst = _tool(tools_a, "list_memories")
    rows = await lst.ainvoke({})

    assert len(rows) == 1
    assert rows[0]["content"] == "Alice fact"
    assert all(r["content"] != "Bob fact" for r in rows)


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_three_named_tools(core_db, user_id, vector_store, embedding_svc):
    tools = build_memory_tools(
        user_id=user_id, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    names = {t.name for t in tools}
    assert names == {"save_memory", "list_memories", "search_memory"}


def test_tool_descriptions_are_non_empty(core_db, user_id, vector_store, embedding_svc):
    tools = build_memory_tools(
        user_id=user_id, db=core_db, vector_store=vector_store, embedding_svc=embedding_svc
    )
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
