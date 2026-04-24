"""Tests for flux_bot.tools.bot — LangChain tools wrapping
flux_core bot Use Cases with user_id closed over.

Tests focus on observable side-effects: rows in bot_outbound_messages
and bot_scheduled_tasks.
"""
from __future__ import annotations

from flux_bot.tools.bot import build_bot_tools


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── send_outbound_message ────────────────────────────────────────────────


async def test_send_outbound_message_inserts_row(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    send = _tool(tools, "send_outbound_message")

    result = await send.ainvoke({"text": "Hello, user!"})

    assert result["status"] == "sent"
    assert "message_id" in result

    # Verify the row exists in the DB.
    row = core_db.connection().execute(
        "SELECT text, user_id FROM bot_outbound_messages WHERE id = ?",
        (result["message_id"],),
    ).fetchone()
    assert row is not None
    assert row["text"] == "Hello, user!"
    assert row["user_id"] == user_id


async def test_send_outbound_message_optional_sender(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    send = _tool(tools, "send_outbound_message")

    result = await send.ainvoke({"text": "Progress update", "sender": "scheduler"})

    assert result["status"] == "sent"
    row = core_db.connection().execute(
        "SELECT sender FROM bot_outbound_messages WHERE id = ?",
        (result["message_id"],),
    ).fetchone()
    assert row["sender"] == "scheduler"


# ── schedule_task ────────────────────────────────────────────────────────


async def test_schedule_task_creates_row(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    schedule = _tool(tools, "schedule_task")

    result = await schedule.ainvoke(
        {
            "prompt": "Check my budget status",
            "schedule_type": "interval",
            "schedule_value": "3600000",
        }
    )

    assert result["status"] == "scheduled"
    assert "task_id" in result

    row = core_db.connection().execute(
        "SELECT prompt, user_id FROM bot_scheduled_tasks WHERE id = ?",
        (result["task_id"],),
    ).fetchone()
    assert row is not None
    assert row["prompt"] == "Check my budget status"
    assert row["user_id"] == user_id


async def test_schedule_task_invalid_type_returns_error(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    schedule = _tool(tools, "schedule_task")

    result = await schedule.ainvoke(
        {
            "prompt": "Do something",
            "schedule_type": "badtype",
            "schedule_value": "123",
        }
    )

    assert result["status"] == "error"


# ── list_tasks ───────────────────────────────────────────────────────────


async def test_list_tasks_returns_scheduled(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    schedule = _tool(tools, "schedule_task")
    lst = _tool(tools, "list_tasks")

    await schedule.ainvoke(
        {
            "prompt": "Daily summary",
            "schedule_type": "cron",
            "schedule_value": "0 9 * * *",
        }
    )

    result = await lst.ainvoke({})

    assert "tasks" in result
    assert len(result["tasks"]) >= 1


# ── cancel_task ──────────────────────────────────────────────────────────


async def test_cancel_task_removes_row(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    schedule = _tool(tools, "schedule_task")
    cancel = _tool(tools, "cancel_task")
    lst = _tool(tools, "list_tasks")

    scheduled = await schedule.ainvoke(
        {
            "prompt": "One-time task",
            "schedule_type": "interval",
            "schedule_value": "60000",
        }
    )
    task_id = scheduled["task_id"]

    result = await cancel.ainvoke({"task_id": task_id})
    after = await lst.ainvoke({})

    assert result["status"] == "cancelled"
    assert result["task_id"] == task_id
    task_ids = {t["id"] for t in after["tasks"]}
    assert task_id not in task_ids


async def test_cancel_nonexistent_task_returns_error(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    cancel = _tool(tools, "cancel_task")

    result = await cancel.ainvoke({"task_id": 999999})

    assert result["status"] == "error"


# ── cross-user isolation ─────────────────────────────────────────────────


async def test_list_tasks_isolates_by_user(core_db, seed_user):
    """User B's task list is empty even when user A has scheduled tasks."""
    user_a = seed_user("tg:alice")
    user_b = seed_user("tg:bob")

    tools_a = build_bot_tools(user_id=user_a, db=core_db)
    await _tool(tools_a, "schedule_task").ainvoke(
        {
            "prompt": "Alice daily summary",
            "schedule_type": "cron",
            "schedule_value": "0 8 * * *",
        }
    )

    tools_b = build_bot_tools(user_id=user_b, db=core_db)
    result = await _tool(tools_b, "list_tasks").ainvoke({})

    task_prompts = [t["prompt"] for t in result["tasks"]]
    assert "Alice daily summary" not in task_prompts, (
        "User B should not see user A's scheduled tasks"
    )


# ── surface sanity ───────────────────────────────────────────────────────


def test_build_returns_four_named_tools(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    names = {t.name for t in tools}
    assert names == {
        "send_outbound_message",
        "schedule_task",
        "list_tasks",
        "cancel_task",
    }


def test_tool_descriptions_are_non_empty(core_db, user_id):
    tools = build_bot_tools(user_id=user_id, db=core_db)
    for t in tools:
        assert t.description and len(t.description) > 10, (
            f"Tool {t.name} has insufficient description: {t.description!r}"
        )
