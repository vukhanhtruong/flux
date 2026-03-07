"""Tests for goal use cases."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.models.goal import GoalOut
from flux_core.use_cases.goals import (
    CreateGoal,
    DeleteGoal,
    DepositToGoal,
    ListGoals,
    WithdrawFromGoal,
)

USER_ID = "tg:12345"
FAKE_ID = uuid4()


def _make_goal(**overrides) -> GoalOut:
    defaults = {
        "id": FAKE_ID,
        "user_id": USER_ID,
        "name": "Vacation",
        "target_amount": Decimal("5000.00"),
        "current_amount": Decimal("0.00"),
        "deadline": date(2026, 12, 31),
        "color": "#3B82F6",
    }
    defaults.update(overrides)
    return GoalOut(**defaults)


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    return uow


# ── CreateGoal ──────────────────────────────────────────────────────────


@patch("flux_core.use_cases.goals.create_goal.SqliteGoalRepository")
async def test_create_goal(mock_repo_cls):
    uow = _mock_uow()
    expected = _make_goal()
    mock_repo_cls.return_value.create.return_value = expected

    uc = CreateGoal(uow)
    result = await uc.execute(
        USER_ID, "Vacation", Decimal("5000.00"),
        deadline=date(2026, 12, 31),
    )

    assert result.name == "Vacation"
    assert result.target_amount == Decimal("5000.00")
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.goals.create_goal.SqliteGoalRepository")
async def test_create_goal_no_deadline(mock_repo_cls):
    uow = _mock_uow()
    expected = _make_goal(deadline=None)
    mock_repo_cls.return_value.create.return_value = expected

    uc = CreateGoal(uow)
    result = await uc.execute(USER_ID, "Vacation", Decimal("5000.00"))

    assert result.deadline is None


# ── ListGoals ───────────────────────────────────────────────────────────


async def test_list_goals():
    goals = [_make_goal(), _make_goal(id=uuid4(), name="Car")]
    repo = MagicMock()
    repo.list_by_user.return_value = goals

    uc = ListGoals(repo)
    result = await uc.execute(USER_ID)

    assert len(result) == 2
    repo.list_by_user.assert_called_once_with(USER_ID)


# ── DepositToGoal ──────────────────────────────────────────────────────


@patch("flux_core.use_cases.goals.deposit_to_goal.SqliteGoalRepository")
async def test_deposit_to_goal(mock_repo_cls):
    uow = _mock_uow()
    expected = _make_goal(current_amount=Decimal("100.00"))
    mock_repo_cls.return_value.deposit.return_value = expected

    uc = DepositToGoal(uow)
    result = await uc.execute(FAKE_ID, USER_ID, Decimal("100.00"))

    assert result.current_amount == Decimal("100.00")
    mock_repo_cls.return_value.deposit.assert_called_once_with(
        FAKE_ID, USER_ID, Decimal("100.00")
    )
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.goals.deposit_to_goal.SqliteGoalRepository")
async def test_deposit_to_goal_not_found(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.deposit.return_value = None

    uc = DepositToGoal(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID, Decimal("100.00"))
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ── WithdrawFromGoal ────────────────────────────────────────────────────


@patch("flux_core.use_cases.goals.withdraw_from_goal.SqliteGoalRepository")
async def test_withdraw_from_goal(mock_repo_cls):
    uow = _mock_uow()
    expected = _make_goal(current_amount=Decimal("50.00"))
    mock_repo_cls.return_value.withdraw.return_value = expected

    uc = WithdrawFromGoal(uow)
    result = await uc.execute(FAKE_ID, USER_ID, Decimal("50.00"))

    assert result.current_amount == Decimal("50.00")
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.goals.withdraw_from_goal.SqliteGoalRepository")
async def test_withdraw_from_goal_not_found(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.withdraw.return_value = None

    uc = WithdrawFromGoal(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID, Decimal("50.00"))
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ── DeleteGoal ──────────────────────────────────────────────────────────


@patch("flux_core.use_cases.goals.delete_goal.SqliteGoalRepository")
async def test_delete_goal(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.delete.return_value = True

    uc = DeleteGoal(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result is True
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.goals.delete_goal.SqliteGoalRepository")
async def test_delete_goal_not_found(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.delete.return_value = False

    uc = DeleteGoal(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result is False
