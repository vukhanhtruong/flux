"""E2E tests for financial MCP tools — subscription billing."""
import json
from uuid import uuid4


def _extract_json(tool_result):
    assert len(tool_result.content) > 0
    return json.loads(tool_result.content[0].text)


async def test_process_subscription_billing_creates_transaction(seeded_server):
    """process_subscription_billing creates expense transaction with correct amount."""
    create_result = await seeded_server.call_tool(
        "create_subscription",
        {
            "name": "Netflix",
            "amount": 15.99,
            "billing_cycle": "monthly",
            "next_date": "2026-04-01",
            "category": "Entertainment",
        },
    )
    sub_id = _extract_json(create_result)["id"]

    result = await seeded_server.call_tool(
        "process_subscription_billing", {"subscription_id": sub_id}
    )
    data = _extract_json(result)
    assert data["subscription_name"] == "Netflix"
    assert data["amount"] == "15.99"
    assert "transaction_id" in data
    assert "billing_date" in data


async def test_process_subscription_billing_not_found(seeded_server):
    """process_subscription_billing returns error dict for missing subscription."""
    fake_id = str(uuid4())
    result = await seeded_server.call_tool(
        "process_subscription_billing", {"subscription_id": fake_id}
    )
    data = _extract_json(result)
    assert "error" in data


async def test_process_subscription_billing_inactive(seeded_server):
    """process_subscription_billing returns error dict for inactive subscription."""
    create_result = await seeded_server.call_tool(
        "create_subscription",
        {
            "name": "Spotify",
            "amount": 9.99,
            "billing_cycle": "monthly",
            "next_date": "2026-04-01",
            "category": "Entertainment",
        },
    )
    sub_id = _extract_json(create_result)["id"]
    await seeded_server.call_tool("toggle_subscription", {"subscription_id": sub_id})

    result = await seeded_server.call_tool(
        "process_subscription_billing", {"subscription_id": sub_id}
    )
    data = _extract_json(result)
    assert "error" in data
