"""Tests for MCP tool execution with mocked dependencies."""
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import FastMCP
from flux_mcp.tools.transaction_tools import register_transaction_tools
from flux_mcp.tools.financial_tools import register_financial_tools
from flux_mcp.tools.analytics_tools import register_analytics_tools
from flux_mcp.tools.memory_tools import register_memory_tools
from flux_mcp.tools.profile_tools import register_profile_tools


def _make_transaction_mcp():
    test_mcp = FastMCP("test-transaction")
    mock_db = AsyncMock()
    mock_embedding = MagicMock()
    mock_embedding.embed.return_value = [0.1] * 384

    async def get_db():
        return mock_db

    def get_embedding():
        return mock_embedding

    def get_user_id():
        return "test-user"

    register_transaction_tools(test_mcp, get_db, get_embedding, get_user_id)
    return test_mcp


def _make_financial_mcp():
    test_mcp = FastMCP("test-financial")
    mock_db = AsyncMock()

    async def get_db():
        return mock_db

    def get_user_id():
        return "test-user"

    register_financial_tools(test_mcp, get_db, get_user_id)
    return test_mcp


def _make_analytics_mcp():
    test_mcp = FastMCP("test-analytics")
    mock_db = AsyncMock()

    async def get_db():
        return mock_db

    def get_user_id():
        return "test-user"

    register_analytics_tools(test_mcp, get_db, get_user_id)
    return test_mcp


def _make_memory_mcp():
    test_mcp = FastMCP("test-memory")
    mock_db = AsyncMock()
    mock_embedding = MagicMock()
    mock_embedding.embed.return_value = [0.1] * 384

    async def get_db():
        return mock_db

    def get_embedding():
        return mock_embedding

    def get_user_id():
        return "test-user"

    register_memory_tools(test_mcp, get_db, get_embedding, get_user_id)
    return test_mcp


def _make_profile_mcp():
    test_mcp = FastMCP("test-profile")
    mock_db = AsyncMock()

    async def get_db():
        return mock_db

    def get_user_id():
        return "test-user"

    register_profile_tools(test_mcp, get_db, get_user_id)
    return test_mcp


# --------------------------------------------------------------------------- #
# Transaction tools
# --------------------------------------------------------------------------- #

async def test_add_transaction_tool():
    test_mcp = _make_transaction_mcp()
    with patch(
        "flux_mcp.tools.transaction_tools.biz.add_transaction",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"id": "abc", "amount": 50.0}
        result = await test_mcp.call_tool(
            "add_transaction",
            {
                "date": "2024-01-15",
                "amount": 50.0,
                "category": "Food",
                "description": "Lunch",
                "transaction_type": "expense",
            },
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_list_transactions_tool():
    test_mcp = _make_transaction_mcp()
    with patch(
        "flux_mcp.tools.transaction_tools.biz.list_transactions",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = []
        result = await test_mcp.call_tool("list_transactions", {})
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_search_transactions_tool():
    test_mcp = _make_transaction_mcp()
    with patch(
        "flux_mcp.tools.transaction_tools.biz.search_transactions",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = []
        result = await test_mcp.call_tool(
            "search_transactions", {"query": "coffee"}
        )
    assert result is not None
    mock_biz.assert_awaited_once()


# --------------------------------------------------------------------------- #
# Financial tools
# --------------------------------------------------------------------------- #

async def test_set_budget_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.set_budget",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"id": "bud1", "category": "Food", "monthly_limit": 500.0}
        result = await test_mcp.call_tool(
            "set_budget", {"category": "Food", "monthly_limit": 500.0}
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_list_budgets_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.list_budgets",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = []
        result = await test_mcp.call_tool("list_budgets", {})
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_create_goal_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.create_goal",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"id": "goal1", "name": "Vacation", "target_amount": 1000.0}
        result = await test_mcp.call_tool(
            "create_goal", {"name": "Vacation", "target_amount": 1000.0}
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_list_goals_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.list_goals",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = []
        result = await test_mcp.call_tool("list_goals", {})
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_create_subscription_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.create_subscription",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"id": "sub1", "name": "Netflix"}
        result = await test_mcp.call_tool(
            "create_subscription",
            {
                "name": "Netflix",
                "amount": 15.0,
                "billing_cycle": "monthly",
                "next_date": "2024-02-01",
                "category": "Entertainment",
            },
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_list_subscriptions_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.list_subscriptions",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = []
        result = await test_mcp.call_tool("list_subscriptions", {})
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_toggle_subscription_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.toggle_subscription",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"id": "sub1", "is_active": False}
        result = await test_mcp.call_tool(
            "toggle_subscription", {"subscription_id": "sub1"}
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_delete_subscription_tool():
    test_mcp = _make_financial_mcp()
    with patch(
        "flux_mcp.tools.financial_tools.biz.delete_subscription",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"deleted": True}
        result = await test_mcp.call_tool(
            "delete_subscription", {"subscription_id": "sub1"}
        )
    assert result is not None
    mock_biz.assert_awaited_once()


# --------------------------------------------------------------------------- #
# Analytics tools
# --------------------------------------------------------------------------- #

async def test_generate_spending_report_tool():
    test_mcp = _make_analytics_mcp()
    with patch(
        "flux_mcp.tools.analytics_tools.biz.generate_spending_report",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"total": 500.0, "by_category": {}}
        result = await test_mcp.call_tool(
            "generate_spending_report",
            {"start_date": "2024-01-01", "end_date": "2024-01-31"},
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_calculate_financial_health_tool():
    test_mcp = _make_analytics_mcp()
    with patch(
        "flux_mcp.tools.analytics_tools.biz.calculate_financial_health",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"score": 75, "grade": "B"}
        result = await test_mcp.call_tool(
            "calculate_financial_health",
            {"start_date": "2024-01-01", "end_date": "2024-01-31"},
        )
    assert result is not None
    mock_biz.assert_awaited_once()


# --------------------------------------------------------------------------- #
# Memory tools
# --------------------------------------------------------------------------- #

async def test_remember_tool():
    test_mcp = _make_memory_mcp()
    with patch(
        "flux_mcp.tools.memory_tools.biz.remember",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = {"id": "mem1", "content": "I prefer dark mode"}
        result = await test_mcp.call_tool(
            "remember",
            {"memory_type": "preference", "content": "I prefer dark mode"},
        )
    assert result is not None
    mock_biz.assert_awaited_once()


async def test_recall_tool():
    test_mcp = _make_memory_mcp()
    with patch(
        "flux_mcp.tools.memory_tools.biz.recall",
        new_callable=AsyncMock,
    ) as mock_biz:
        mock_biz.return_value = []
        result = await test_mcp.call_tool("recall", {"query": "preferences"})
    assert result is not None
    mock_biz.assert_awaited_once()


# --------------------------------------------------------------------------- #
# Profile tools
# --------------------------------------------------------------------------- #

async def test_update_preferences_returns_profile():
    test_mcp = _make_profile_mcp()

    from flux_core.models.user_profile import UserProfile
    mock_profile = UserProfile(
        user_id="test-user",
        username="testuser",
        channel="telegram",
        platform_id="12345",
        currency="USD",
        timezone="UTC",
    )
    mock_repo_instance = AsyncMock()
    mock_repo_instance.update.return_value = mock_profile
    mock_repo_class = MagicMock(return_value=mock_repo_instance)

    with patch("flux_mcp.tools.profile_tools.UserProfileRepository", mock_repo_class):
        result = await test_mcp.call_tool(
            "update_preferences",
            {"currency": "USD", "timezone": "UTC", "username": "testuser"},
        )

    assert result is not None
    mock_repo_instance.update.assert_awaited_once()


async def test_update_preferences_no_args_returns_current():
    test_mcp = _make_profile_mcp()

    from flux_core.models.user_profile import UserProfile
    mock_profile = UserProfile(
        user_id="test-user",
        username="testuser",
        channel="telegram",
        platform_id="12345",
        currency="VND",
        timezone="Asia/Ho_Chi_Minh",
    )
    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_by_user_id.return_value = mock_profile
    mock_repo_class = MagicMock(return_value=mock_repo_instance)

    with patch("flux_mcp.tools.profile_tools.UserProfileRepository", mock_repo_class):
        result = await test_mcp.call_tool("update_preferences", {})

    assert result is not None
    mock_repo_instance.get_by_user_id.assert_awaited_once_with("test-user")
