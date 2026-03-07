"""Tests for SqliteTransactionRepository."""
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from flux_core.models.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionType,
    TransactionUpdate,
)
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository


@pytest.fixture
def repo(conn):
    return SqliteTransactionRepository(conn)


def _make_txn(user_id: str, **overrides) -> TransactionCreate:
    defaults = dict(
        user_id=user_id,
        date=date(2026, 3, 1),
        amount=Decimal("100.00"),
        category="Food",
        description="Lunch",
        type=TransactionType.expense,
    )
    defaults.update(overrides)
    return TransactionCreate(**defaults)


class TestCreate:
    def test_creates_transaction(self, repo, user_id):
        txn = _make_txn(user_id)
        result = repo.create(txn)
        assert isinstance(result, TransactionOut)
        assert isinstance(result.id, UUID)
        assert result.user_id == user_id
        assert result.amount == Decimal("100.00")
        assert result.category == "Food"
        assert result.type == TransactionType.expense
        assert result.is_recurring is False
        assert result.tags == []

    def test_creates_with_tags_and_recurring(self, repo, user_id):
        txn = _make_txn(user_id, tags=["restaurant", "work"], is_recurring=True)
        result = repo.create(txn)
        assert result.tags == ["restaurant", "work"]
        assert result.is_recurring is True


class TestGetById:
    def test_found(self, repo, user_id):
        created = repo.create(_make_txn(user_id))
        result = repo.get_by_id(created.id, user_id)
        assert result is not None
        assert result.id == created.id

    def test_not_found(self, repo, user_id):
        fake_id = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.get_by_id(fake_id, user_id) is None

    def test_wrong_user(self, repo, user_id, conn):
        created = repo.create(_make_txn(user_id))
        assert repo.get_by_id(created.id, "other:user") is None


class TestGetByIds:
    def test_returns_matching(self, repo, user_id):
        t1 = repo.create(_make_txn(user_id, description="A"))
        t2 = repo.create(_make_txn(user_id, description="B"))
        results = repo.get_by_ids([t1.id, t2.id])
        assert len(results) == 2
        ids = {r.id for r in results}
        assert t1.id in ids
        assert t2.id in ids

    def test_empty_list(self, repo):
        assert repo.get_by_ids([]) == []


class TestListByUser:
    def test_basic_list(self, repo, user_id):
        repo.create(_make_txn(user_id, description="A"))
        repo.create(_make_txn(user_id, description="B"))
        results = repo.list_by_user(user_id)
        assert len(results) == 2

    def test_filter_by_date_range(self, repo, user_id):
        repo.create(_make_txn(user_id, date=date(2026, 1, 1)))
        repo.create(_make_txn(user_id, date=date(2026, 3, 15)))
        repo.create(_make_txn(user_id, date=date(2026, 6, 1)))
        results = repo.list_by_user(
            user_id, start_date=date(2026, 2, 1), end_date=date(2026, 4, 1)
        )
        assert len(results) == 1

    def test_filter_by_categories(self, repo, user_id):
        repo.create(_make_txn(user_id, category="Food"))
        repo.create(_make_txn(user_id, category="Transport"))
        repo.create(_make_txn(user_id, category="Health"))
        results = repo.list_by_user(user_id, categories=["Food", "Health"])
        assert len(results) == 2

    def test_filter_by_type(self, repo, user_id):
        repo.create(_make_txn(user_id, type=TransactionType.income))
        repo.create(_make_txn(user_id, type=TransactionType.expense))
        results = repo.list_by_user(user_id, txn_type="income")
        assert len(results) == 1
        assert results[0].type == TransactionType.income

    def test_limit_offset(self, repo, user_id):
        for i in range(5):
            repo.create(_make_txn(user_id, description=f"Txn {i}"))
        results = repo.list_by_user(user_id, limit=2, offset=1)
        assert len(results) == 2

    def test_order_by_date_desc(self, repo, user_id):
        repo.create(_make_txn(user_id, date=date(2026, 1, 1)))
        repo.create(_make_txn(user_id, date=date(2026, 3, 1)))
        results = repo.list_by_user(user_id)
        assert results[0].date >= results[1].date


class TestUpdate:
    def test_update_fields(self, repo, user_id):
        created = repo.create(_make_txn(user_id))
        updates = TransactionUpdate(category="Transport", amount=Decimal("200.00"))
        result = repo.update(created.id, user_id, updates)
        assert result is not None
        assert result.category == "Transport"
        assert result.amount == Decimal("200.00")

    def test_update_type(self, repo, user_id):
        created = repo.create(_make_txn(user_id, type=TransactionType.expense))
        updates = TransactionUpdate(type=TransactionType.income)
        result = repo.update(created.id, user_id, updates)
        assert result.type == TransactionType.income

    def test_update_tags(self, repo, user_id):
        created = repo.create(_make_txn(user_id))
        updates = TransactionUpdate(tags=["groceries"])
        result = repo.update(created.id, user_id, updates)
        assert result.tags == ["groceries"]

    def test_empty_update_returns_current(self, repo, user_id):
        created = repo.create(_make_txn(user_id))
        result = repo.update(created.id, user_id, TransactionUpdate())
        assert result.id == created.id

    def test_update_not_found(self, repo, user_id):
        fake_id = UUID("00000000-0000-0000-0000-000000000001")
        result = repo.update(fake_id, user_id, TransactionUpdate(category="X"))
        assert result is None


class TestDelete:
    def test_delete_existing(self, repo, user_id):
        created = repo.create(_make_txn(user_id))
        assert repo.delete(created.id, user_id) is True
        assert repo.get_by_id(created.id, user_id) is None

    def test_delete_nonexistent(self, repo, user_id):
        fake_id = UUID("00000000-0000-0000-0000-000000000001")
        assert repo.delete(fake_id, user_id) is False


class TestGetSummary:
    def test_summary(self, repo, user_id):
        repo.create(
            _make_txn(user_id, type=TransactionType.income, amount=Decimal("1000.00"))
        )
        repo.create(
            _make_txn(user_id, type=TransactionType.expense, amount=Decimal("300.00"))
        )
        repo.create(
            _make_txn(user_id, type=TransactionType.expense, amount=Decimal("200.00"))
        )
        result = repo.get_summary(user_id, date(2026, 1, 1), date(2026, 12, 31))
        assert Decimal(str(result["total_income"])) == Decimal("1000.00")
        assert Decimal(str(result["total_expenses"])) == Decimal("500.00")
        assert result["count"] == 3


class TestGetCategoryBreakdown:
    def test_breakdown(self, repo, user_id):
        repo.create(
            _make_txn(user_id, category="Food", amount=Decimal("100.00"))
        )
        repo.create(
            _make_txn(user_id, category="Food", amount=Decimal("50.00"))
        )
        repo.create(
            _make_txn(user_id, category="Transport", amount=Decimal("200.00"))
        )
        result = repo.get_category_breakdown(
            user_id, date(2026, 1, 1), date(2026, 12, 31)
        )
        assert len(result) == 2
        # ordered by total DESC
        assert result[0]["category"] == "Transport"
        assert Decimal(str(result[0]["total"])) == Decimal("200.00")
        assert result[1]["category"] == "Food"
        assert result[1]["count"] == 2
