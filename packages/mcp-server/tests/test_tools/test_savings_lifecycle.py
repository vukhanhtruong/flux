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


# ── cron derivation tests ────────────────────────────────────────────────────


def test_derive_savings_cron_yearly():
    from flux_mcp.tools.savings_tools import _derive_savings_cron
    assert _derive_savings_cron("yearly", date(2026, 3, 1)) == "0 0 1 3 *"


def test_derive_savings_cron_monthly():
    from flux_mcp.tools.savings_tools import _derive_savings_cron
    assert _derive_savings_cron("monthly", date(2026, 6, 15)) == "0 0 15 * *"


def test_derive_savings_cron_quarterly():
    from flux_mcp.tools.savings_tools import _derive_savings_cron
    result = _derive_savings_cron("quarterly", date(2026, 3, 1))
    assert result == "0 0 1 3,6,9,12 *"


def test_derive_savings_cron_quarterly_start_month_2():
    from flux_mcp.tools.savings_tools import _derive_savings_cron
    result = _derive_savings_cron("quarterly", date(2026, 2, 10))
    assert result == "0 0 10 2,5,8,11 *"


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
    call_kwargs = scheduler_repo.create.call_args
    assert call_kwargs.kwargs["schedule_date"] == "2027-03-01"
    assert call_kwargs.kwargs["user_id"] == USER_ID


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
