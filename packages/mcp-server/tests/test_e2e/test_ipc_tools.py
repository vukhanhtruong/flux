"""E2E tests for IPC MCP tools — scheduling and messaging."""
import json


def _extract_json(tool_result):
    assert len(tool_result.content) > 0
    return json.loads(tool_result.content[0].text)


async def test_schedule_task_with_cron(seeded_server):
    """schedule_task creates a cron task with timezone conversion."""
    result = await seeded_server.call_tool(
        "schedule_task",
        {
            "prompt": "Daily report",
            "schedule_type": "cron",
            "schedule_value": "0 9 * * *",
        },
    )
    data = _extract_json(result)
    assert data["status"] == "scheduled"
    assert "task_id" in data


async def test_scheduled_task_lifecycle(seeded_server):
    """Full lifecycle: create -> list -> pause -> resume -> cancel."""
    # Create
    create_result = await seeded_server.call_tool(
        "schedule_task",
        {
            "prompt": "Lifecycle test",
            "schedule_type": "interval",
            "schedule_value": "3600000",
        },
    )
    task_id = _extract_json(create_result)["task_id"]

    # List — should contain the new active task
    list_result = await seeded_server.call_tool("list_scheduled_tasks", {})
    list_data = _extract_json(list_result)
    tasks = list_data["tasks"]
    assert any(t["id"] == task_id for t in tasks)

    # Pause
    pause_result = await seeded_server.call_tool(
        "pause_scheduled_task", {"task_id": task_id}
    )
    pause_data = _extract_json(pause_result)
    assert pause_data["status"] == "paused"

    # Resume
    resume_result = await seeded_server.call_tool(
        "resume_scheduled_task", {"task_id": task_id}
    )
    resume_data = _extract_json(resume_result)
    assert resume_data["status"] == "resumed"

    # Cancel
    cancel_result = await seeded_server.call_tool(
        "cancel_scheduled_task", {"task_id": task_id}
    )
    cancel_data = _extract_json(cancel_result)
    assert cancel_data["status"] == "cancelled"


async def test_send_message_with_sender(seeded_server):
    """send_message passes sender through to the use case."""
    result = await seeded_server.call_tool(
        "send_message",
        {"text": "Hello from test", "sender": "scheduler"},
    )
    data = _extract_json(result)
    assert "message_id" in data
    assert data["status"] == "sent"
