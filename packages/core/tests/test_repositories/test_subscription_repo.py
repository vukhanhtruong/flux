"""Tests for SqliteSubscriptionRepository."""
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from flux_core.models.subscription import BillingCycle, SubscriptionCreate, SubscriptionOut
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository


@pytest.fixture
def repo(conn):
    return SqliteSubscriptionRepository(conn)


def _make_sub(user_id: str, **overrides) -> SubscriptionCreate:
    defaults = dict(
        user_id=user_id,
        name="Netflix",
        amount=Decimal("15.00"),
        billing_cycle=BillingCycle.monthly,
        next_date=date(2026, 4, 1),
        category="Entertainment",
    )
    defaults.update(overrides)
    return SubscriptionCreate(**defaults)


class TestCreate:
    def test_creates_subscription(self, repo, user_id):
        result = repo.create(_make_sub(user_id))
        assert isinstance(result, SubscriptionOut)
        assert isinstance(result.id, UUID)
        assert result.name == "Netflix"
        assert result.amount == Decimal("15.00")
        assert result.billing_cycle == BillingCycle.monthly
        assert result.active is True


class TestGet:
    def test_found(self, repo, user_id):
        created = repo.create(_make_sub(user_id))
        result = repo.get(created.id, user_id)
        assert result is not None
        assert result.id == created.id

    def test_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.get(fake, user_id) is None


class TestListByUser:
    def test_active_only(self, repo, user_id):
        repo.create(_make_sub(user_id, name="Netflix"))
        s2 = repo.create(_make_sub(user_id, name="Spotify"))
        repo.toggle_active(s2.id, user_id)  # deactivate
        results = repo.list_by_user(user_id, active_only=True)
        assert len(results) == 1
        assert results[0].name == "Netflix"

    def test_all(self, repo, user_id):
        repo.create(_make_sub(user_id, name="Netflix"))
        s2 = repo.create(_make_sub(user_id, name="Spotify"))
        repo.toggle_active(s2.id, user_id)
        results = repo.list_by_user(user_id, active_only=False)
        assert len(results) == 2

    def test_order_by_next_date(self, repo, user_id):
        repo.create(_make_sub(user_id, name="Later", next_date=date(2026, 6, 1)))
        repo.create(_make_sub(user_id, name="Sooner", next_date=date(2026, 4, 1)))
        results = repo.list_by_user(user_id)
        assert results[0].name == "Sooner"


class TestGetDue:
    def test_returns_due(self, repo, user_id):
        repo.create(_make_sub(user_id, next_date=date(2026, 3, 1)))
        repo.create(_make_sub(user_id, next_date=date(2026, 5, 1)))
        results = repo.get_due(user_id, date(2026, 3, 15))
        assert len(results) == 1

    def test_ignores_inactive(self, repo, user_id):
        s = repo.create(_make_sub(user_id, next_date=date(2026, 3, 1)))
        repo.toggle_active(s.id, user_id)
        results = repo.get_due(user_id, date(2026, 3, 15))
        assert len(results) == 0


class TestAdvanceNextDate:
    def test_monthly(self, repo, user_id):
        created = repo.create(
            _make_sub(user_id, billing_cycle=BillingCycle.monthly, next_date=date(2026, 3, 15))
        )
        result = repo.advance_next_date(created.id, user_id)
        assert result is not None
        assert result.next_date == date(2026, 4, 15)

    def test_yearly(self, repo, user_id):
        created = repo.create(
            _make_sub(user_id, billing_cycle=BillingCycle.yearly, next_date=date(2026, 3, 15))
        )
        result = repo.advance_next_date(created.id, user_id)
        assert result.next_date == date(2027, 3, 15)

    def test_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.advance_next_date(fake, user_id) is None


class TestToggleActive:
    def test_deactivate(self, repo, user_id):
        created = repo.create(_make_sub(user_id))
        result = repo.toggle_active(created.id, user_id)
        assert result.active is False

    def test_reactivate(self, repo, user_id):
        created = repo.create(_make_sub(user_id))
        repo.toggle_active(created.id, user_id)
        result = repo.toggle_active(created.id, user_id)
        assert result.active is True


class TestDelete:
    def test_delete_existing(self, repo, user_id):
        created = repo.create(_make_sub(user_id))
        assert repo.delete(created.id, user_id) is True

    def test_delete_nonexistent(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.delete(fake, user_id) is False
