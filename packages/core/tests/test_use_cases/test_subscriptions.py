"""Tests for subscription use cases."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.models.subscription import BillingCycle, SubscriptionOut
from flux_core.use_cases.subscriptions import (
    CreateSubscription,
    DeleteSubscription,
    ListSubscriptions,
    ToggleSubscription,
)

USER_ID = "tg:12345"
FAKE_ID = uuid4()


def _make_sub(**overrides) -> SubscriptionOut:
    defaults = {
        "id": FAKE_ID,
        "user_id": USER_ID,
        "name": "Netflix",
        "amount": Decimal("15.99"),
        "billing_cycle": BillingCycle.monthly,
        "next_date": date(2026, 4, 1),
        "category": "entertainment",
        "active": True,
    }
    defaults.update(overrides)
    return SubscriptionOut(**defaults)


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    uow.add_event = MagicMock()
    return uow


# ── CreateSubscription ──────────────────────────────────────────────────


@patch(
    "flux_core.use_cases.subscriptions.create_subscription"
    ".SqliteBotScheduledTaskRepository"
)
@patch(
    "flux_core.use_cases.subscriptions.create_subscription"
    ".SqliteSubscriptionRepository"
)
async def test_create_subscription(mock_sub_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    expected = _make_sub()
    mock_sub_repo_cls.return_value.create.return_value = expected

    uc = CreateSubscription(uow)
    result = await uc.execute(
        USER_ID,
        "Netflix",
        Decimal("15.99"),
        BillingCycle.monthly,
        date(2026, 4, 1),
        "entertainment",
    )

    assert result.name == "Netflix"
    mock_sub_repo_cls.assert_called_once_with(uow.conn)
    mock_task_repo_cls.assert_called_once_with(uow.conn)
    mock_task_repo_cls.return_value.create.assert_called_once()
    # Verify scheduled task was created with correct subscription_id
    call_kwargs = mock_task_repo_cls.return_value.create.call_args
    assert call_kwargs.kwargs["subscription_id"] == str(FAKE_ID)
    assert call_kwargs.kwargs["schedule_type"] == "cron"
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch(
    "flux_core.use_cases.subscriptions.create_subscription"
    ".SqliteBotScheduledTaskRepository"
)
@patch(
    "flux_core.use_cases.subscriptions.create_subscription"
    ".SqliteSubscriptionRepository"
)
async def test_create_yearly_subscription(mock_sub_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    expected = _make_sub(billing_cycle=BillingCycle.yearly, next_date=date(2027, 1, 15))
    mock_sub_repo_cls.return_value.create.return_value = expected

    uc = CreateSubscription(uow)
    await uc.execute(
        USER_ID,
        "Netflix",
        Decimal("120.00"),
        BillingCycle.yearly,
        date(2027, 1, 15),
        "entertainment",
    )

    call_kwargs = mock_task_repo_cls.return_value.create.call_args
    assert call_kwargs.kwargs["schedule_value"] == "0 0 15 1 *"


# ── ListSubscriptions ──────────────────────────────────────────────────


async def test_list_subscriptions():
    subs = [_make_sub(), _make_sub(id=uuid4(), name="Spotify")]
    repo = MagicMock()
    repo.list_by_user.return_value = subs

    uc = ListSubscriptions(repo)
    result = await uc.execute(USER_ID)

    assert len(result) == 2
    repo.list_by_user.assert_called_once_with(USER_ID, True)


async def test_list_subscriptions_include_inactive():
    repo = MagicMock()
    repo.list_by_user.return_value = []

    uc = ListSubscriptions(repo)
    await uc.execute(USER_ID, active_only=False)

    repo.list_by_user.assert_called_once_with(USER_ID, False)


# ── ToggleSubscription ──────────────────────────────────────────────────


@patch(
    "flux_core.use_cases.subscriptions.toggle_subscription"
    ".SqliteSubscriptionRepository"
)
async def test_toggle_subscription_deactivate(mock_sub_repo_cls):
    uow = _mock_uow()
    expected = _make_sub(active=False)
    mock_sub_repo_cls.return_value.toggle_active.return_value = expected

    uc = ToggleSubscription(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result.active is False
    # Should pause the scheduler
    uow.conn.execute.assert_called()
    uow.commit.assert_called_once()


@patch(
    "flux_core.use_cases.subscriptions.toggle_subscription"
    ".SqliteSubscriptionRepository"
)
async def test_toggle_subscription_activate(mock_sub_repo_cls):
    uow = _mock_uow()
    expected = _make_sub(active=True)
    mock_sub_repo_cls.return_value.toggle_active.return_value = expected

    uc = ToggleSubscription(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result.active is True
    uow.conn.execute.assert_called()
    uow.commit.assert_called_once()


@patch(
    "flux_core.use_cases.subscriptions.toggle_subscription"
    ".SqliteSubscriptionRepository"
)
async def test_toggle_subscription_not_found(mock_sub_repo_cls):
    uow = _mock_uow()
    mock_sub_repo_cls.return_value.toggle_active.return_value = None

    uc = ToggleSubscription(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID)
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ── DeleteSubscription ──────────────────────────────────────────────────


@patch(
    "flux_core.use_cases.subscriptions.delete_subscription"
    ".SqliteSubscriptionRepository"
)
@patch(
    "flux_core.use_cases.subscriptions.delete_subscription"
    ".SqliteBotScheduledTaskRepository"
)
async def test_delete_subscription(mock_task_repo_cls, mock_sub_repo_cls):
    uow = _mock_uow()
    mock_sub_repo_cls.return_value.delete.return_value = True

    uc = DeleteSubscription(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result is True
    mock_task_repo_cls.return_value.delete_by_subscription.assert_called_once_with(
        str(FAKE_ID)
    )
    mock_sub_repo_cls.return_value.delete.assert_called_once_with(FAKE_ID, USER_ID)
    uow.commit.assert_called_once()
