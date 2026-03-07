"""Tests for SqliteAssetRepository."""
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from flux_core.models.asset import AssetCreate, AssetFrequency, AssetOut, AssetType
from flux_core.sqlite.asset_repo import SqliteAssetRepository


@pytest.fixture
def repo(conn):
    return SqliteAssetRepository(conn)


def _make_asset(user_id: str, **overrides) -> AssetCreate:
    defaults = dict(
        user_id=user_id,
        name="Savings Account",
        amount=Decimal("10000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Bank",
        asset_type=AssetType.income,
    )
    defaults.update(overrides)
    return AssetCreate(**defaults)


class TestCreate:
    def test_creates_asset(self, repo, user_id):
        result = repo.create(_make_asset(user_id))
        assert isinstance(result, AssetOut)
        assert isinstance(result.id, UUID)
        assert result.name == "Savings Account"
        assert result.amount == Decimal("10000.00")
        assert result.interest_rate == Decimal("5.00")
        assert result.active is True
        assert result.asset_type == AssetType.income

    def test_creates_savings_asset(self, repo, user_id):
        result = repo.create(
            _make_asset(
                user_id,
                asset_type=AssetType.savings,
                principal_amount=Decimal("5000.00"),
                compound_frequency="quarterly",
                maturity_date=date(2027, 1, 1),
                start_date=date(2026, 1, 1),
            )
        )
        assert result.asset_type == AssetType.savings
        assert result.principal_amount == Decimal("5000.00")
        assert result.compound_frequency == "quarterly"
        assert result.maturity_date == date(2027, 1, 1)
        assert result.start_date == date(2026, 1, 1)


class TestGet:
    def test_found(self, repo, user_id):
        created = repo.create(_make_asset(user_id))
        result = repo.get(created.id, user_id)
        assert result is not None
        assert result.id == created.id

    def test_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.get(fake, user_id) is None


class TestListByUser:
    def test_active_only(self, repo, user_id):
        repo.create(_make_asset(user_id, name="A"))
        b = repo.create(_make_asset(user_id, name="B"))
        repo.deactivate(b.id, user_id)
        results = repo.list_by_user(user_id, active_only=True)
        assert len(results) == 1

    def test_all(self, repo, user_id):
        repo.create(_make_asset(user_id, name="A"))
        b = repo.create(_make_asset(user_id, name="B"))
        repo.deactivate(b.id, user_id)
        results = repo.list_by_user(user_id, active_only=False)
        assert len(results) == 2

    def test_filter_by_asset_type(self, repo, user_id):
        repo.create(_make_asset(user_id, asset_type=AssetType.income))
        repo.create(_make_asset(user_id, asset_type=AssetType.savings))
        results = repo.list_by_user(user_id, asset_type="savings")
        assert len(results) == 1
        assert results[0].asset_type == AssetType.savings


class TestGetDue:
    def test_returns_due(self, repo, user_id):
        repo.create(_make_asset(user_id, next_date=date(2026, 3, 1)))
        repo.create(_make_asset(user_id, next_date=date(2026, 5, 1)))
        results = repo.get_due(user_id, date(2026, 3, 15))
        assert len(results) == 1

    def test_ignores_inactive(self, repo, user_id):
        a = repo.create(_make_asset(user_id, next_date=date(2026, 3, 1)))
        repo.deactivate(a.id, user_id)
        assert repo.get_due(user_id, date(2026, 3, 15)) == []


class TestAdvanceNextDate:
    def test_monthly(self, repo, user_id):
        created = repo.create(
            _make_asset(user_id, frequency=AssetFrequency.monthly, next_date=date(2026, 3, 15))
        )
        result = repo.advance_next_date(created.id, user_id)
        assert result.next_date == date(2026, 4, 15)

    def test_quarterly(self, repo, user_id):
        created = repo.create(
            _make_asset(user_id, frequency=AssetFrequency.quarterly, next_date=date(2026, 3, 15))
        )
        result = repo.advance_next_date(created.id, user_id)
        assert result.next_date == date(2026, 6, 15)

    def test_yearly(self, repo, user_id):
        created = repo.create(
            _make_asset(user_id, frequency=AssetFrequency.yearly, next_date=date(2026, 3, 15))
        )
        result = repo.advance_next_date(created.id, user_id)
        assert result.next_date == date(2027, 3, 15)

    def test_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.advance_next_date(fake, user_id) is None


class TestUpdateAmount:
    def test_updates(self, repo, user_id):
        created = repo.create(_make_asset(user_id))
        result = repo.update_amount(created.id, user_id, Decimal("20000.00"))
        assert result.amount == Decimal("20000.00")

    def test_not_found(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.update_amount(fake, user_id, Decimal("100.00")) is None


class TestDeactivate:
    def test_deactivates(self, repo, user_id):
        created = repo.create(_make_asset(user_id))
        result = repo.deactivate(created.id, user_id)
        assert result.active is False


class TestDelete:
    def test_delete_existing(self, repo, user_id):
        created = repo.create(_make_asset(user_id))
        assert repo.delete(created.id, user_id) is True

    def test_delete_nonexistent(self, repo, user_id):
        fake = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.delete(fake, user_id) is False
