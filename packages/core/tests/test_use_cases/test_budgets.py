"""Tests for budget use cases."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.models.budget import BudgetOut
from flux_core.use_cases.budgets import ListBudgets, RemoveBudget, SetBudget

USER_ID = "tg:12345"
FAKE_ID = uuid4()


def _make_budget(**overrides) -> BudgetOut:
    defaults = {
        "id": FAKE_ID,
        "user_id": USER_ID,
        "category": "food",
        "monthly_limit": Decimal("500.00"),
    }
    defaults.update(overrides)
    return BudgetOut(**defaults)


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    return uow


# ── SetBudget ───────────────────────────────────────────────────────────


@patch("flux_core.use_cases.budgets.set_budget.SqliteBudgetRepository")
async def test_set_budget(mock_repo_cls):
    uow = _mock_uow()
    expected = _make_budget()
    mock_repo_cls.return_value.set.return_value = expected

    uc = SetBudget(uow)
    result = await uc.execute(USER_ID, "food", Decimal("500.00"))

    assert result.category == "food"
    assert result.monthly_limit == Decimal("500.00")
    mock_repo_cls.assert_called_once_with(uow.conn)
    uow.commit.assert_called_once()


# ── ListBudgets ─────────────────────────────────────────────────────────


async def test_list_budgets():
    budgets = [_make_budget(), _make_budget(id=uuid4(), category="transport")]
    repo = MagicMock()
    repo.list_by_user.return_value = budgets

    uc = ListBudgets(repo)
    result = await uc.execute(USER_ID)

    assert len(result) == 2
    repo.list_by_user.assert_called_once_with(USER_ID)


async def test_list_budgets_empty():
    repo = MagicMock()
    repo.list_by_user.return_value = []

    uc = ListBudgets(repo)
    result = await uc.execute(USER_ID)

    assert result == []


# ── RemoveBudget ────────────────────────────────────────────────────────


@patch("flux_core.use_cases.budgets.remove_budget.SqliteBudgetRepository")
async def test_remove_budget(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.remove.return_value = True

    uc = RemoveBudget(uow)
    result = await uc.execute(USER_ID, "food")

    assert result is True
    mock_repo_cls.return_value.remove.assert_called_once_with(USER_ID, "food")
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.budgets.remove_budget.SqliteBudgetRepository")
async def test_remove_budget_not_found(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.remove.return_value = False

    uc = RemoveBudget(uow)
    result = await uc.execute(USER_ID, "nonexistent")

    assert result is False
