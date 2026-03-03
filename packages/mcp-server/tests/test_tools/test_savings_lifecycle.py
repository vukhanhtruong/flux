"""Unit tests for savings tool lifecycle hooks (scheduler side effects)."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID
import pytest

from flux_core.models.asset import AssetOut, AssetFrequency, AssetType


ASSET_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_ID = "tg:456"

_SAVINGS_ACTIVE = AssetOut(
    id=ASSET_UUID, user_id=USER_ID, name="Bank Deposit",
    amount=Decimal("100000000"), interest_rate=Decimal("5"),
    frequency=AssetFrequency.yearly, next_date=date(2027, 3, 1),
    category="savings", active=True, asset_type=AssetType.savings,
    principal_amount=Decimal("100000000"), compound_frequency="yearly",
    maturity_date=date(2028, 3, 1), start_date=date(2026, 3, 1),
)


@pytest.fixture
def scheduler_repo():
    return AsyncMock()


@pytest.fixture
def asset_repo():
    mock = AsyncMock()
    mock.create.return_value = _SAVINGS_ACTIVE
    return mock


# ── lifecycle tests ──────────────────────────────────────────────────────────


async def test_create_savings_with_scheduler(asset_repo, scheduler_repo):
    from flux_mcp.tools.savings_tools import _create_savings_with_scheduler

    result = await _create_savings_with_scheduler(
        user_id=USER_ID,
        name="Bank Deposit",
        amount=100000000.0,
        interest_rate=5.0,
        compound_frequency="yearly",
        start_date="2026-03-01",
        maturity_date="2028-03-01",
        category="savings",
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["asset_type"] == "savings"
    scheduler_repo.create.assert_called_once()
    call_kwargs = scheduler_repo.create.call_args.kwargs
    assert call_kwargs["schedule_date"] == "2027-03-01"
    assert call_kwargs["user_id"] == USER_ID
    assert "cron" not in call_kwargs
    # Regular prompt (not maturity) since 2027-03-01 < 2028-03-01
    assert "matures today" not in call_kwargs["prompt"]
    assert "Process savings interest" in call_kwargs["prompt"]


async def test_create_savings_maturity_prompt(asset_repo, scheduler_repo):
    """When next_date == maturity_date, the prompt should include maturity language."""
    from flux_mcp.tools.savings_tools import _create_savings_with_scheduler

    short_asset = AssetOut(
        id=ASSET_UUID, user_id=USER_ID, name="Short Deposit",
        amount=Decimal("50000000"), interest_rate=Decimal("5"),
        frequency=AssetFrequency.yearly, next_date=date(2026, 9, 1),
        category="savings", active=True, asset_type=AssetType.savings,
        principal_amount=Decimal("50000000"), compound_frequency="yearly",
        maturity_date=date(2026, 9, 1), start_date=date(2026, 3, 1),
    )
    asset_repo.create.return_value = short_asset

    await _create_savings_with_scheduler(
        user_id=USER_ID, name="Short Deposit", amount=50000000.0,
        interest_rate=5.0, compound_frequency="yearly",
        start_date="2026-03-01", maturity_date="2026-09-01",
        category="savings", asset_repo=asset_repo, scheduler_repo=scheduler_repo,
    )

    call_kwargs = scheduler_repo.create.call_args.kwargs
    assert "matures today" in call_kwargs["prompt"]
    assert "withdraw" in call_kwargs["prompt"].lower()


async def test_create_savings_regular_prompt(asset_repo, scheduler_repo):
    """When next_date < maturity_date, the prompt should be a simple process prompt."""
    from flux_mcp.tools.savings_tools import _create_savings_with_scheduler

    await _create_savings_with_scheduler(
        user_id=USER_ID, name="Bank Deposit", amount=100000000.0,
        interest_rate=5.0, compound_frequency="yearly",
        start_date="2026-03-01", maturity_date="2028-03-01",
        category="savings", asset_repo=asset_repo, scheduler_repo=scheduler_repo,
    )

    call_kwargs = scheduler_repo.create.call_args.kwargs
    assert "matures today" not in call_kwargs["prompt"]
    assert "Process savings interest" in call_kwargs["prompt"]


async def test_close_savings_deletes_scheduler(asset_repo, scheduler_repo):
    from flux_mcp.tools.savings_tools import _close_savings_with_scheduler

    asset_repo.get.return_value = _SAVINGS_ACTIVE
    asset_repo.deactivate.return_value = AssetOut(
        **{**_SAVINGS_ACTIVE.model_dump(), "active": False}
    )

    result = await _close_savings_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["active"] is False
    scheduler_repo.delete.assert_called_once_with(str(ASSET_UUID))


async def test_delete_asset_deletes_savings_scheduler(asset_repo, scheduler_repo):
    from flux_mcp.tools.savings_tools import _delete_savings_with_scheduler

    asset_repo.delete.return_value = True

    result = await _delete_savings_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["success"] is True
    scheduler_repo.delete.assert_called_once_with(str(ASSET_UUID))


async def test_process_interest_reschedules_next(asset_repo, scheduler_repo):
    """After interest is applied and deposit is not matured, a new once task is created."""
    from flux_mcp.tools.savings_tools import _process_interest_with_scheduler

    asset_repo.update_amount.return_value = None
    # advance_next_date returns asset with next_date moved forward to maturity
    advanced = AssetOut(
        **{**_SAVINGS_ACTIVE.model_dump(), "next_date": date(2028, 3, 1)}
    )
    asset_repo.advance_next_date.return_value = advanced
    # First get() is called inside biz.process_savings_interest (returns active asset);
    # second get() is called inside _process_interest_with_scheduler to read new next_date.
    asset_repo.get.side_effect = [_SAVINGS_ACTIVE, advanced]

    result = await _process_interest_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["matured"] is False
    scheduler_repo.create.assert_called_once()
    call_kwargs = scheduler_repo.create.call_args.kwargs
    assert call_kwargs["schedule_date"] == "2028-03-01"
    # 2028-03-01 == maturity_date on _SAVINGS_ACTIVE, so prompt should be maturity prompt
    assert "matures today" in call_kwargs["prompt"]


async def test_withdraw_savings_deletes_scheduler(asset_repo, scheduler_repo):
    from flux_mcp.tools.savings_tools import _withdraw_savings_with_scheduler
    from flux_core.models.transaction import TransactionOut, TransactionType
    from datetime import datetime, timezone

    asset_repo.get.return_value = _SAVINGS_ACTIVE
    asset_repo.deactivate.return_value = AssetOut(
        **{**_SAVINGS_ACTIVE.model_dump(), "active": False}
    )
    txn_repo = AsyncMock()
    txn_repo.create.return_value = TransactionOut(
        id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        user_id=USER_ID, date=date(2027, 3, 1),
        amount=Decimal("100000000"), category="savings",
        description="Withdrawal from savings: Bank Deposit",
        type=TransactionType.income, is_recurring=False, tags=[],
        created_at=datetime(2027, 3, 1, tzinfo=timezone.utc),
    )

    result = await _withdraw_savings_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        txn_repo=txn_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["withdrawn_amount"] == "100000000"
    assert result["transaction_id"] is not None
    scheduler_repo.delete.assert_called_once_with(str(ASSET_UUID))


async def test_process_interest_no_reschedule_on_maturity(asset_repo, scheduler_repo):
    """When interest matures the deposit, no new task is scheduled."""
    from flux_mcp.tools.savings_tools import _process_interest_with_scheduler

    # Asset where current next_date is at maturity (final interest event)
    at_maturity = AssetOut(
        **{**_SAVINGS_ACTIVE.model_dump(),
           "next_date": date(2028, 3, 1),
           "maturity_date": date(2028, 3, 1)}
    )
    asset_repo.get.return_value = at_maturity
    asset_repo.update_amount.return_value = None
    # advance_next_date would put next_date past maturity
    past_maturity = AssetOut(
        **{**at_maturity.model_dump(), "next_date": date(2029, 3, 1)}
    )
    asset_repo.advance_next_date.return_value = past_maturity
    asset_repo.deactivate.return_value = AssetOut(
        **{**at_maturity.model_dump(), "active": False}
    )

    result = await _process_interest_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["matured"] is True
    scheduler_repo.create.assert_not_called()
