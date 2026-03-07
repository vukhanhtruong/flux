"""Tests for SqliteBudgetRepository."""
from decimal import Decimal

import pytest
from flux_core.models.budget import BudgetOut, BudgetSet
from flux_core.sqlite.budget_repo import SqliteBudgetRepository


@pytest.fixture
def repo(conn):
    return SqliteBudgetRepository(conn)


def _make_budget(user_id: str, **overrides) -> BudgetSet:
    defaults = dict(
        user_id=user_id,
        category="Food",
        monthly_limit=Decimal("500.00"),
    )
    defaults.update(overrides)
    return BudgetSet(**defaults)


class TestSet:
    def test_creates_budget(self, repo, user_id):
        result = repo.set(_make_budget(user_id))
        assert isinstance(result, BudgetOut)
        assert result.category == "Food"
        assert result.monthly_limit == Decimal("500.00")

    def test_upsert_updates_existing(self, repo, user_id):
        repo.set(_make_budget(user_id, monthly_limit=Decimal("500.00")))
        result = repo.set(_make_budget(user_id, monthly_limit=Decimal("800.00")))
        assert result.monthly_limit == Decimal("800.00")
        # should still be only one budget for this category
        all_budgets = repo.list_by_user(user_id)
        food_budgets = [b for b in all_budgets if b.category == "Food"]
        assert len(food_budgets) == 1


class TestListByUser:
    def test_lists_all(self, repo, user_id):
        repo.set(_make_budget(user_id, category="Food"))
        repo.set(_make_budget(user_id, category="Transport"))
        results = repo.list_by_user(user_id)
        assert len(results) == 2
        categories = [b.category for b in results]
        assert categories == ["Food", "Transport"]  # sorted

    def test_empty_list(self, repo, user_id):
        assert repo.list_by_user(user_id) == []


class TestGetByCategory:
    def test_found(self, repo, user_id):
        repo.set(_make_budget(user_id))
        result = repo.get_by_category(user_id, "Food")
        assert result is not None
        assert result.category == "Food"

    def test_not_found(self, repo, user_id):
        assert repo.get_by_category(user_id, "Nonexistent") is None


class TestRemove:
    def test_removes_existing(self, repo, user_id):
        repo.set(_make_budget(user_id))
        assert repo.remove(user_id, "Food") is True
        assert repo.get_by_category(user_id, "Food") is None

    def test_remove_nonexistent(self, repo, user_id):
        assert repo.remove(user_id, "Ghost") is False
