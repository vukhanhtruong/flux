"""Unit tests for subscription tool lifecycle hooks (scheduler side effects)."""
from datetime import date, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID
import pytest

from flux_core.models.subscription import SubscriptionOut, BillingCycle
from flux_mcp.db.subscription_scheduler_repo import _derive_cron, _to_utc_midnight


SUB_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_ID = "tg:123"

_SUB_ACTIVE = SubscriptionOut(
    id=SUB_UUID, user_id=USER_ID, name="Netflix",
    amount=Decimal("200000"), billing_cycle=BillingCycle.monthly,
    next_date=date(2026, 3, 5), category="entertainment", active=True,
)
_SUB_INACTIVE = SubscriptionOut(
    id=SUB_UUID, user_id=USER_ID, name="Netflix",
    amount=Decimal("200000"), billing_cycle=BillingCycle.monthly,
    next_date=date(2026, 3, 5), category="entertainment", active=False,
)


@pytest.fixture
def scheduler_repo():
    return AsyncMock()


@pytest.fixture
def sub_repo():
    mock = AsyncMock()
    mock.create.return_value = _SUB_ACTIVE
    mock.toggle_active.return_value = _SUB_INACTIVE
    return mock


async def test_create_subscription_creates_scheduler(sub_repo, scheduler_repo):
    from flux_mcp.tools.financial_tools import _create_subscription_with_scheduler

    result = await _create_subscription_with_scheduler(
        user_id=USER_ID,
        name="Netflix",
        amount=200000.0,
        billing_cycle="monthly",
        next_date="2026-03-05",
        category="entertainment",
        sub_repo=sub_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["name"] == "Netflix"
    scheduler_repo.create.assert_called_once()
    call_kwargs = scheduler_repo.create.call_args
    assert call_kwargs.kwargs["cron"] == "0 0 5 * *"
    assert call_kwargs.kwargs["user_id"] == USER_ID
    assert str(SUB_UUID) in call_kwargs.kwargs["subscription_id"]


async def test_toggle_inactive_pauses_scheduler(sub_repo, scheduler_repo):
    from flux_mcp.tools.financial_tools import _toggle_subscription_with_scheduler

    result = await _toggle_subscription_with_scheduler(
        subscription_id=str(SUB_UUID),
        user_id=USER_ID,
        sub_repo=sub_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["active"] is False
    scheduler_repo.pause.assert_called_once_with(str(SUB_UUID))
    scheduler_repo.resume.assert_not_called()


async def test_toggle_active_resumes_scheduler():
    sub_repo = AsyncMock()
    sub_repo.toggle_active.return_value = _SUB_ACTIVE  # now active
    scheduler_repo = AsyncMock()

    from flux_mcp.tools.financial_tools import _toggle_subscription_with_scheduler

    result = await _toggle_subscription_with_scheduler(
        subscription_id=str(SUB_UUID),
        user_id=USER_ID,
        sub_repo=sub_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["active"] is True
    scheduler_repo.resume.assert_called_once()
    scheduler_repo.pause.assert_not_called()


async def test_delete_subscription_deletes_scheduler(sub_repo, scheduler_repo):
    sub_repo.delete.return_value = True

    from flux_mcp.tools.financial_tools import _delete_subscription_with_scheduler

    result = await _delete_subscription_with_scheduler(
        subscription_id=str(SUB_UUID),
        user_id=USER_ID,
        sub_repo=sub_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["success"] is True
    scheduler_repo.delete.assert_called_once_with(str(SUB_UUID))


def test_derive_cron_monthly():
    assert _derive_cron(BillingCycle.monthly, date(2026, 3, 1)) == "0 0 1 * *"
    assert _derive_cron(BillingCycle.monthly, date(2026, 3, 15)) == "0 0 15 * *"
    assert _derive_cron(BillingCycle.monthly, date(2026, 3, 28)) == "0 0 28 * *"


def test_derive_cron_yearly():
    assert _derive_cron(BillingCycle.yearly, date(2026, 3, 15)) == "0 0 15 3 *"
    assert _derive_cron(BillingCycle.yearly, date(2026, 12, 31)) == "0 0 31 12 *"
    assert _derive_cron(BillingCycle.yearly, date(2026, 1, 1)) == "0 0 1 1 *"


def test_to_utc_midnight():
    result = _to_utc_midnight(date(2026, 3, 5))
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 5
    assert result.hour == 0
    assert result.minute == 0
    assert result.tzinfo == timezone.utc
