"""Tests for SqliteGoalRepository."""
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from flux_core.models.goal import GoalCreate, GoalOut, GoalUpdate
from flux_core.sqlite.goal_repo import SqliteGoalRepository


@pytest.fixture
def repo(conn):
    return SqliteGoalRepository(conn)


def _make_goal(user_id: str, **overrides) -> GoalCreate:
    defaults = dict(
        user_id=user_id,
        name="Vacation",
        target_amount=Decimal("5000.00"),
    )
    defaults.update(overrides)
    return GoalCreate(**defaults)


class TestCreate:
    def test_creates_goal(self, repo, user_id):
        result = repo.create(_make_goal(user_id))
        assert isinstance(result, GoalOut)
        assert isinstance(result.id, UUID)
        assert result.name == "Vacation"
        assert result.target_amount == Decimal("5000.00")
        assert result.current_amount == Decimal("0")
        assert result.color == "#3B82F6"
        assert result.deadline is None

    def test_creates_with_deadline(self, repo, user_id):
        result = repo.create(_make_goal(user_id, deadline=date(2027, 1, 1)))
        assert result.deadline == date(2027, 1, 1)


class TestGetById:
    def test_found(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        result = repo.get_by_id(created.id, user_id)
        assert result is not None
        assert result.id == created.id

    def test_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.get_by_id(fake, user_id) is None


class TestListByUser:
    def test_lists_sorted_by_name(self, repo, user_id):
        repo.create(_make_goal(user_id, name="Zebra"))
        repo.create(_make_goal(user_id, name="Apple"))
        results = repo.list_by_user(user_id)
        assert len(results) == 2
        assert results[0].name == "Apple"
        assert results[1].name == "Zebra"

    def test_empty(self, repo, user_id):
        assert repo.list_by_user(user_id) == []


class TestUpdate:
    def test_update_name(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        result = repo.update(created.id, user_id, GoalUpdate(name="New Name"))
        assert result is not None
        assert result.name == "New Name"

    def test_update_target_amount(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        result = repo.update(
            created.id, user_id, GoalUpdate(target_amount=Decimal("10000.00"))
        )
        assert result.target_amount == Decimal("10000.00")

    def test_empty_update(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        result = repo.update(created.id, user_id, GoalUpdate())
        assert result.id == created.id

    def test_update_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        result = repo.update(fake, user_id, GoalUpdate(name="X"))
        assert result is None


class TestDeposit:
    def test_deposit(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        result = repo.deposit(created.id, user_id, Decimal("1000.00"))
        assert result is not None
        assert result.current_amount == Decimal("1000.00")

    def test_deposit_accumulates(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        repo.deposit(created.id, user_id, Decimal("100.00"))
        result = repo.deposit(created.id, user_id, Decimal("200.00"))
        assert result.current_amount == Decimal("300.00")

    def test_deposit_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.deposit(fake, user_id, Decimal("100.00")) is None


class TestWithdraw:
    def test_withdraw(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        repo.deposit(created.id, user_id, Decimal("500.00"))
        result = repo.withdraw(created.id, user_id, Decimal("200.00"))
        assert result is not None
        assert result.current_amount == Decimal("300.00")

    def test_withdraw_floors_at_zero(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        repo.deposit(created.id, user_id, Decimal("100.00"))
        result = repo.withdraw(created.id, user_id, Decimal("500.00"))
        assert result.current_amount == Decimal("0")

    def test_withdraw_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.withdraw(fake, user_id, Decimal("100.00")) is None


class TestDelete:
    def test_delete_existing(self, repo, user_id):
        created = repo.create(_make_goal(user_id))
        assert repo.delete(created.id, user_id) is True

    def test_delete_nonexistent(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.delete(fake, user_id) is False
