"""Unit tests for subscription tool lifecycle hooks (scheduler side effects)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
import pytest

from flux_core.models.subscription import SubscriptionOut, BillingCycle


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
