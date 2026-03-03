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
    # Savings tools
    create_savings_deposit,
    process_savings_interest,
    list_savings,
    close_savings_early,
)
from flux_core.models.budget import BudgetOut
from flux_core.models.goal import GoalOut
from flux_core.models.subscription import SubscriptionOut, BillingCycle
from flux_core.models.asset import AssetCreate, AssetOut, AssetFrequency, AssetType
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
    assert result["asset_type"] == "income"
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
    assert result[0]["asset_type"] == "income"
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


# Savings tools tests
async def test_create_savings_deposit():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Bank Deposit",
        amount=Decimal("100000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 1, 1),
        category="savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="yearly",
        maturity_date=date(2028, 1, 1),
        start_date=date(2026, 1, 1),
    )

    result = await create_savings_deposit(
        user_id="tg:123",
        name="Bank Deposit",
        amount=100000000,
        interest_rate=5.0,
        compound_frequency="yearly",
        start_date="2026-01-01",
        maturity_date="2028-01-01",
        category="savings",
        repo=mock_repo,
    )

    assert result["asset_type"] == "savings"
    assert result["principal_amount"] == "100000000"
    assert result["compound_frequency"] == "yearly"
    mock_repo.create.assert_called_once()
    created = mock_repo.create.call_args[0][0]
    assert isinstance(created, AssetCreate)
    assert created.asset_type == AssetType.savings
    assert created.principal_amount == Decimal("100000000")
    assert created.frequency == AssetFrequency.yearly
    assert created.next_date == date(2027, 1, 1)


async def test_create_savings_deposit_monthly():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Monthly Deposit",
        amount=Decimal("100000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 2, 1),
        category="savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="monthly",
        maturity_date=date(2027, 1, 1),
        start_date=date(2026, 1, 1),
    )

    await create_savings_deposit(
        user_id="tg:123",
        name="Monthly Deposit",
        amount=100000000,
        interest_rate=5.0,
        compound_frequency="monthly",
        start_date="2026-01-01",
        maturity_date="2027-01-01",
        category="savings",
        repo=mock_repo,
    )

    created = mock_repo.create.call_args[0][0]
    assert created.next_date == date(2026, 2, 1)
    assert created.frequency == AssetFrequency.monthly


async def test_process_savings_interest_annual():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    asset = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Bank Deposit",
        amount=Decimal("100000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 1, 1),
        category="savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="yearly",
        maturity_date=date(2028, 1, 1),
        start_date=date(2026, 1, 1),
    )
    mock_repo.get.return_value = asset
    mock_repo.update_amount.return_value = AssetOut(
        **{**asset.model_dump(), "amount": Decimal("105000000")}
    )
    mock_repo.advance_next_date.return_value = AssetOut(
        **{**asset.model_dump(), "amount": Decimal("105000000"),
           "next_date": date(2027, 7, 1)}
    )

    result = await process_savings_interest(
        asset_id=str(test_uuid),
        user_id="tg:123",
        repo=mock_repo,
    )

    assert result["interest_applied"] == "5000000.00"
    assert result["new_balance"] == "105000000.00"
    assert result["matured"] is False
    mock_repo.update_amount.assert_called_once()
    mock_repo.advance_next_date.assert_called_once()


async def test_process_savings_interest_monthly():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    asset = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Bank Deposit",
        amount=Decimal("100000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 2, 1),
        category="savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="monthly",
        maturity_date=date(2027, 1, 1),
        start_date=date(2026, 1, 1),
    )
    mock_repo.get.return_value = asset
    # 100M * (5/100/12) = 416666.67
    new_amount = Decimal("100000000") + Decimal("416666.67")
    mock_repo.update_amount.return_value = AssetOut(
        **{**asset.model_dump(), "amount": new_amount}
    )
    mock_repo.advance_next_date.return_value = AssetOut(
        **{**asset.model_dump(), "amount": new_amount,
           "next_date": date(2026, 3, 1)}
    )

    result = await process_savings_interest(
        asset_id=str(test_uuid),
        user_id="tg:123",
        repo=mock_repo,
    )

    assert result["interest_applied"] == "416666.67"
    assert result["matured"] is False


async def test_process_savings_interest_maturity():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    asset = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Bank Deposit",
        amount=Decimal("100000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 12, 1),
        category="savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="yearly",
        maturity_date=date(2028, 1, 1),
        start_date=date(2026, 1, 1),
    )
    mock_repo.get.return_value = asset
    new_amount = Decimal("105000000")
    mock_repo.update_amount.return_value = AssetOut(
        **{**asset.model_dump(), "amount": new_amount}
    )
    # After advance, next_date > maturity_date
    mock_repo.advance_next_date.return_value = AssetOut(
        **{**asset.model_dump(), "amount": new_amount,
           "next_date": date(2028, 12, 1)}
    )
    mock_repo.deactivate.return_value = AssetOut(
        **{**asset.model_dump(), "amount": new_amount,
           "next_date": date(2028, 12, 1), "active": False}
    )

    result = await process_savings_interest(
        asset_id=str(test_uuid),
        user_id="tg:123",
        repo=mock_repo,
    )

    assert result["matured"] is True
    assert "maturity_message" in result
    mock_repo.deactivate.assert_called_once()


async def test_process_savings_interest_exactly_at_maturity_not_yet_matured():
    """When advanced next_date == maturity_date, deposit is NOT matured yet."""
    from flux_core.tools.financial_tools import process_savings_interest

    asset_uuid = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    asset = AssetOut(
        id=asset_uuid, user_id="tg:456", name="Bank Deposit",
        amount=Decimal("100000000"), interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly, next_date=date(2027, 3, 1),
        category="savings", active=True, asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"), compound_frequency="yearly",
        maturity_date=date(2028, 3, 1), start_date=date(2026, 3, 1),
    )
    mock_repo = AsyncMock()
    mock_repo.get.return_value = asset
    mock_repo.update_amount.return_value = None
    # After advancing, next_date lands exactly on maturity_date (not past it)
    mock_repo.advance_next_date.return_value = AssetOut(
        **{**asset.model_dump(), "next_date": date(2028, 3, 1)}
    )

    result = await process_savings_interest(str(asset_uuid), "tg:456", mock_repo)

    assert result["matured"] is False
    mock_repo.deactivate.assert_not_called()


async def test_process_savings_interest_inactive_raises():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.get.return_value = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Bank Deposit",
        amount=Decimal("100000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 1, 1),
        category="savings",
        active=False,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="yearly",
        maturity_date=date(2028, 1, 1),
        start_date=date(2026, 1, 1),
    )

    with pytest.raises(ValueError, match="not active"):
        await process_savings_interest(
            asset_id=str(test_uuid),
            user_id="tg:123",
            repo=mock_repo,
        )


async def test_process_savings_interest_not_found_raises():
    mock_repo = AsyncMock()
    mock_repo.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await process_savings_interest(
            asset_id="12345678-1234-5678-1234-567812345678",
            user_id="tg:123",
            repo=mock_repo,
        )


async def test_list_savings():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        AssetOut(
            id=test_uuid,
            user_id="tg:123",
            name="Bank Deposit",
            amount=Decimal("105000000"),
            interest_rate=Decimal("5"),
            frequency=AssetFrequency.yearly,
            next_date=date(2027, 1, 1),
            category="savings",
            active=True,
            asset_type=AssetType.savings,
            principal_amount=Decimal("100000000"),
            compound_frequency="yearly",
            maturity_date=date(2028, 1, 1),
            start_date=date(2026, 1, 1),
        )
    ]

    result = await list_savings(
        user_id="tg:123",
        repo=mock_repo,
    )

    assert len(result) == 1
    assert result[0]["interest_earned"] == "5000000"
    mock_repo.list_by_user.assert_called_once_with(
        "tg:123", True, asset_type="savings"
    )


async def test_close_savings_early():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    asset = AssetOut(
        id=test_uuid,
        user_id="tg:123",
        name="Bank Deposit",
        amount=Decimal("105000000"),
        interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 1, 1),
        category="savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("100000000"),
        compound_frequency="yearly",
        maturity_date=date(2028, 1, 1),
        start_date=date(2026, 1, 1),
    )
    mock_repo.get.return_value = asset
    mock_repo.deactivate.return_value = AssetOut(
        **{**asset.model_dump(), "active": False}
    )

    result = await close_savings_early(
        asset_id=str(test_uuid),
        user_id="tg:123",
        repo=mock_repo,
    )

    assert result["active"] is False
    mock_repo.deactivate.assert_called_once()


async def test_create_savings_short_term_schedules_at_maturity():
    """When maturity < first compound date, next_date should be set to maturity_date.

    Example: 6-month savings with yearly compounding — schedule interest
    at maturity (2026-09-01) instead of the first yearly date (2027-03-01).
    """
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = AssetOut(
        id=test_uuid, user_id="tg:123", name="Short Deposit",
        amount=Decimal("100000000.00"), interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly, next_date=date(2026, 9, 1),
        category="Savings", active=True, asset_type=AssetType.savings,
        principal_amount=Decimal("100000000.00"), compound_frequency="yearly",
        maturity_date=date(2026, 9, 1), start_date=date(2026, 3, 1),
    )

    result = await create_savings_deposit(
        user_id="tg:123",
        name="Short Deposit",
        amount=100_000_000,
        interest_rate=5.0,
        compound_frequency="yearly",
        start_date="2026-03-01",
        maturity_date="2026-09-01",  # 6 months — shorter than yearly
        category="Savings",
        repo=mock_repo,
    )

    assert result["next_date"] == "2026-09-01"
    created_asset = mock_repo.create.call_args[0][0]
    assert created_asset.next_date == date(2026, 9, 1)


async def test_create_savings_short_term_quarterly_schedules_at_maturity():
    """2-month savings with quarterly compounding schedules at maturity."""
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = AssetOut(
        id=test_uuid, user_id="tg:123", name="Too Short",
        amount=Decimal("50000000.00"), interest_rate=Decimal("4.00"),
        frequency=AssetFrequency.quarterly, next_date=date(2026, 5, 1),
        category="Savings", active=True, asset_type=AssetType.savings,
        principal_amount=Decimal("50000000.00"), compound_frequency="quarterly",
        maturity_date=date(2026, 5, 1), start_date=date(2026, 3, 1),
    )

    result = await create_savings_deposit(
        user_id="tg:123",
        name="Too Short",
        amount=50_000_000,
        interest_rate=4.0,
        compound_frequency="quarterly",
        start_date="2026-03-01",
        maturity_date="2026-05-01",  # 2 months — shorter than quarterly
        category="Savings",
        repo=mock_repo,
    )

    assert result["next_date"] == "2026-05-01"
    created_asset = mock_repo.create.call_args[0][0]
    assert created_asset.next_date == date(2026, 5, 1)
