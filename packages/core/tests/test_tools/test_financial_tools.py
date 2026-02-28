from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
import pytest

from flux_core.tools.financial_tools import (
    # Budget tools
    set_budget,
    list_budgets,
    remove_budget,
    # Goal tools
    create_goal,
    list_goals,
    deposit_to_goal,
    withdraw_from_goal,
    delete_goal,
    # Subscription tools
    create_subscription,
    list_subscriptions,
    advance_subscription,
    toggle_subscription,
    delete_subscription,
    process_subscription_billing,
    # Asset tools
    create_asset,
    list_assets,
    advance_asset,
    delete_asset,
)
from flux_core.models.budget import BudgetOut
from flux_core.models.goal import GoalOut
from flux_core.models.subscription import SubscriptionOut, BillingCycle
from flux_core.models.asset import AssetOut, AssetFrequency
from flux_core.models.transaction import TransactionOut, TransactionType


# Budget tests
@pytest.mark.asyncio
async def test_set_budget():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.set.return_value = BudgetOut(
        id=test_uuid,
        user_id="test_user",
        category="Food",
        monthly_limit=Decimal("500.00")
    )

    result = await set_budget(
        user_id="test_user",
        category="Food",
        monthly_limit=500.00,
        repo=mock_repo
    )

    assert result["id"] == str(test_uuid)
    assert result["category"] == "Food"
    assert result["monthly_limit"] == "500.00"
    mock_repo.set.assert_called_once()


@pytest.mark.asyncio
async def test_list_budgets():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        BudgetOut(
            id=test_uuid,
            user_id="test_user",
            category="Food",
            monthly_limit=Decimal("500.00")
        )
    ]

    result = await list_budgets(
        user_id="test_user",
        repo=mock_repo
    )

    assert len(result) == 1
    assert result[0]["category"] == "Food"
    mock_repo.list_by_user.assert_called_once_with("test_user")


@pytest.mark.asyncio
async def test_remove_budget():
    mock_repo = AsyncMock()
    mock_repo.remove.return_value = True

    result = await remove_budget(
        user_id="test_user",
        category="Food",
        repo=mock_repo
    )

    assert result["success"] is True
    mock_repo.remove.assert_called_once_with("test_user", "Food")


# Goal tests
@pytest.mark.asyncio
async def test_create_goal():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = GoalOut(
        id=test_uuid,
        user_id="test_user",
        name="Vacation",
        target_amount=Decimal("5000.00"),
        current_amount=Decimal("0.00"),
        deadline=date(2026, 12, 31),
        color="#3B82F6"
    )

    result = await create_goal(
        user_id="test_user",
        name="Vacation",
        target_amount=5000.00,
        deadline="2026-12-31",
        color="#3B82F6",
        repo=mock_repo
    )

    assert result["id"] == str(test_uuid)
    assert result["name"] == "Vacation"
    assert result["target_amount"] == "5000.00"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_list_goals():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        GoalOut(
            id=test_uuid,
            user_id="test_user",
            name="Vacation",
            target_amount=Decimal("5000.00"),
            current_amount=Decimal("1000.00"),
            deadline=date(2026, 12, 31),
            color="#3B82F6"
        )
    ]

    result = await list_goals(
        user_id="test_user",
        repo=mock_repo
    )

    assert len(result) == 1
    assert result[0]["name"] == "Vacation"
    assert result[0]["current_amount"] == "1000.00"
    mock_repo.list_by_user.assert_called_once_with("test_user")


@pytest.mark.asyncio
async def test_deposit_to_goal():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.deposit.return_value = GoalOut(
        id=test_uuid,
        user_id="test_user",
        name="Vacation",
        target_amount=Decimal("5000.00"),
        current_amount=Decimal("1200.00"),
        deadline=date(2026, 12, 31),
        color="#3B82F6"
    )

    result = await deposit_to_goal(
        goal_id=str(test_uuid),
        user_id="test_user",
        amount=200.00,
        repo=mock_repo
    )

    assert result["current_amount"] == "1200.00"
    mock_repo.deposit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_goal():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.delete.return_value = True

    result = await delete_goal(
        goal_id=str(test_uuid),
        user_id="test_user",
        repo=mock_repo
    )

    assert result["success"] is True
    mock_repo.delete.assert_called_once()


# Subscription tests
@pytest.mark.asyncio
async def test_create_subscription():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = SubscriptionOut(
        id=test_uuid,
        user_id="test_user",
        name="Netflix",
        amount=Decimal("15.99"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2026, 2, 15),
        category="Entertainment",
        active=True
    )

    result = await create_subscription(
        user_id="test_user",
        name="Netflix",
        amount=15.99,
        billing_cycle="monthly",
        next_date="2026-02-15",
        category="Entertainment",
        repo=mock_repo
    )

    assert result["id"] == str(test_uuid)
    assert result["name"] == "Netflix"
    assert result["amount"] == "15.99"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_list_subscriptions():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        SubscriptionOut(
            id=test_uuid,
            user_id="test_user",
            name="Netflix",
            amount=Decimal("15.99"),
            billing_cycle=BillingCycle.monthly,
            next_date=date(2026, 2, 15),
            category="Entertainment",
            active=True
        )
    ]

    result = await list_subscriptions(
        user_id="test_user",
        active_only=True,
        repo=mock_repo
    )

    assert len(result) == 1
    assert result[0]["name"] == "Netflix"
    mock_repo.list_by_user.assert_called_once_with("test_user", True)


@pytest.mark.asyncio
async def test_toggle_subscription():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.toggle_active.return_value = SubscriptionOut(
        id=test_uuid,
        user_id="test_user",
        name="Netflix",
        amount=Decimal("15.99"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2026, 2, 15),
        category="Entertainment",
        active=False
    )

    result = await toggle_subscription(
        subscription_id=str(test_uuid),
        user_id="test_user",
        repo=mock_repo
    )

    assert result["active"] is False
    mock_repo.toggle_active.assert_called_once()


# Asset tests
@pytest.mark.asyncio
async def test_create_asset():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = AssetOut(
        id=test_uuid,
        user_id="test_user",
        name="Salary",
        amount=Decimal("5000.00"),
        interest_rate=Decimal("0"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 3, 1),
        category="Income",
        active=True
    )

    result = await create_asset(
        user_id="test_user",
        name="Salary",
        amount=5000.00,
        interest_rate=0.0,
        frequency="monthly",
        next_date="2026-03-01",
        category="Income",
        repo=mock_repo
    )

    assert result["id"] == str(test_uuid)
    assert result["name"] == "Salary"
    assert result["amount"] == "5000.00"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_list_assets():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        AssetOut(
            id=test_uuid,
            user_id="test_user",
            name="Salary",
            amount=Decimal("5000.00"),
            interest_rate=Decimal("0"),
            frequency=AssetFrequency.monthly,
            next_date=date(2026, 3, 1),
            category="Income",
            active=True
        )
    ]

    result = await list_assets(
        user_id="test_user",
        active_only=True,
        repo=mock_repo
    )

    assert len(result) == 1
    assert result[0]["name"] == "Salary"
    mock_repo.list_by_user.assert_called_once_with("test_user", True)


@pytest.mark.asyncio
async def test_process_subscription_billing_creates_transaction_and_advances():
    sub_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    txn_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    user_id = "tg:123"

    mock_sub_repo = AsyncMock()
    mock_sub_repo.get.return_value = SubscriptionOut(
        id=sub_id,
        user_id=user_id,
        name="Google One",
        amount=Decimal("30000"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2026, 3, 1),
        category="utilities",
        active=True,
    )
    mock_sub_repo.advance_next_date.return_value = SubscriptionOut(
        id=sub_id,
        user_id=user_id,
        name="Google One",
        amount=Decimal("30000"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2026, 4, 1),
        category="utilities",
        active=True,
    )

    mock_txn_repo = AsyncMock()
    mock_txn_repo.create.return_value = TransactionOut(
        id=txn_id,
        user_id=user_id,
        date=date(2026, 3, 1),
        amount=Decimal("30000"),
        category="utilities",
        description="Google One subscription",
        type=TransactionType.expense,
        is_recurring=True,
        tags=[],
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    mock_embedding = MagicMock()
    mock_embedding.embed.return_value = [0.1] * 384

    result = await process_subscription_billing(
        subscription_id=str(sub_id),
        user_id=user_id,
        sub_repo=mock_sub_repo,
        txn_repo=mock_txn_repo,
        embedding_service=mock_embedding,
    )

    assert result["transaction"]["amount"] == "30000"
    assert result["transaction"]["type"] == "expense"
    assert result["transaction"]["is_recurring"] is True
    assert result["transaction"]["description"] == "Google One subscription"
    assert result["subscription"]["next_date"] == "2026-04-01"
    mock_txn_repo.create.assert_called_once()
    mock_sub_repo.advance_next_date.assert_called_once_with(sub_id, user_id)


@pytest.mark.asyncio
async def test_process_subscription_billing_rejects_inactive():
    sub_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    mock_sub_repo = AsyncMock()
    mock_sub_repo.get.return_value = SubscriptionOut(
        id=sub_id,
        user_id="tg:123",
        name="Google One",
        amount=Decimal("30000"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2026, 3, 1),
        category="utilities",
        active=False,
    )

    with pytest.raises(ValueError, match="not active"):
        await process_subscription_billing(
            subscription_id=str(sub_id),
            user_id="tg:123",
            sub_repo=mock_sub_repo,
            txn_repo=AsyncMock(),
            embedding_service=MagicMock(),
        )


@pytest.mark.asyncio
async def test_process_subscription_billing_not_found():
    mock_sub_repo = AsyncMock()
    mock_sub_repo.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await process_subscription_billing(
            subscription_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            user_id="tg:123",
            sub_repo=mock_sub_repo,
            txn_repo=AsyncMock(),
            embedding_service=MagicMock(),
        )
