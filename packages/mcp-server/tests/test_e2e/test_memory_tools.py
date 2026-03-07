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
