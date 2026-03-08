"""E2E tests for memory MCP tools."""
import json


def _extract_json(tool_result):
    assert len(tool_result.content) > 0
    return json.loads(tool_result.content[0].text)


async def test_remember_stores_memory(seeded_server):
    """remember() stores a memory with correct type and returns response."""
    result = await seeded_server.call_tool(
        "remember",
        {"memory_type": "preference", "content": "User prefers dark mode"},
    )
    data = _extract_json(result)
    assert "id" in data
    assert data["memory_type"] == "preference"
    assert data["content"] == "User prefers dark mode"


async def test_list_memories_returns_stored_memories(seeded_server):
    """list_memories() returns memories, optionally filtered by type."""
    # Create two memories with different types
    await seeded_server.call_tool(
        "remember",
        {"memory_type": "preference", "content": "Prefers morning workouts"},
    )
    await seeded_server.call_tool(
        "remember",
        {"memory_type": "fact", "content": "Met with Alice on Monday"},
    )

    # List all memories
    result = await seeded_server.call_tool("list_memories", {})
    data = _extract_json(result)
    assert isinstance(data, list)
    assert len(data) >= 2
    # Each item should have expected fields
    for item in data:
        assert "id" in item
        assert "memory_type" in item
        assert "content" in item
        assert "created_at" in item
        assert isinstance(item["created_at"], str)

    # Filter by memory_type
    result_filtered = await seeded_server.call_tool(
        "list_memories", {"memory_type": "preference"}
    )
    filtered = _extract_json(result_filtered)
    assert isinstance(filtered, list)
    assert len(filtered) >= 1
    assert all(m["memory_type"] == "preference" for m in filtered)


async def test_list_memories_with_limit(seeded_server):
    """list_memories() respects the limit parameter."""
    for i in range(3):
        await seeded_server.call_tool(
            "remember",
            {"memory_type": "fact", "content": f"Fact number {i}"},
        )
    result = await seeded_server.call_tool("list_memories", {"limit": 2})
    data = _extract_json(result)
    assert isinstance(data, list)
    assert len(data) <= 2


async def test_recall_returns_formatted_results(seeded_server):
    """recall() returns memories with created_at as string."""
    await seeded_server.call_tool(
        "remember",
        {"memory_type": "preference", "content": "Likes Thai food"},
    )
    result = await seeded_server.call_tool(
        "recall", {"query": "food preferences", "limit": 5}
    )
    data = _extract_json(result)
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "id" in item
        assert "memory_type" in item
        assert "content" in item
        assert "created_at" in item
        assert isinstance(item["created_at"], str)
