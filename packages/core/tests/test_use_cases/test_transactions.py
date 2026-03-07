"""Tests for transaction use cases."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.models.transaction import (
    TransactionOut,
    TransactionType,
    TransactionUpdate,
)
from flux_core.use_cases.transactions import (
    AddTransaction,
    DeleteTransaction,
    ListTransactions,
    SearchTransactions,
    UpdateTransaction,
)

USER_ID = "tg:12345"
FAKE_ID = uuid4()
FAKE_NOW = datetime(2026, 3, 7, 12, 0, 0)
FAKE_EMBEDDING = [0.1] * 384


def _make_txn_out(**overrides) -> TransactionOut:
    defaults = {
        "id": FAKE_ID,
        "user_id": USER_ID,
        "date": date(2026, 3, 7),
        "amount": Decimal("42.50"),
        "category": "food",
        "description": "lunch",
        "type": TransactionType.expense,
        "is_recurring": False,
        "tags": [],
        "created_at": FAKE_NOW,
    }
    defaults.update(overrides)
    return TransactionOut(**defaults)


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    uow.add_vector = MagicMock()
    uow.add_event = MagicMock()
    uow.delete_vector = MagicMock()
    return uow


def _mock_embedding_svc():
    svc = MagicMock()
    svc.embed.return_value = FAKE_EMBEDDING
    return svc


# ── AddTransaction ──────────────────────────────────────────────────────


@patch("flux_core.use_cases.transactions.add_transaction.SqliteTransactionRepository")
async def test_add_transaction(mock_repo_cls):
    uow = _mock_uow()
    svc = _mock_embedding_svc()
    expected = _make_txn_out()
    mock_repo_cls.return_value.create.return_value = expected

    uc = AddTransaction(uow, svc)
    result = await uc.execute(
        user_id=USER_ID,
        date=date(2026, 3, 7),
        amount=Decimal("42.50"),
        category="food",
        description="lunch",
        transaction_type=TransactionType.expense,
    )

    assert result.id == FAKE_ID
    assert result.amount == Decimal("42.50")
    mock_repo_cls.assert_called_once_with(uow.conn)
    mock_repo_cls.return_value.create.assert_called_once()
    svc.embed.assert_called_once_with("food lunch")
    uow.add_vector.assert_called_once()
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.transactions.add_transaction.SqliteTransactionRepository")
async def test_add_transaction_with_tags(mock_repo_cls):
    uow = _mock_uow()
    svc = _mock_embedding_svc()
    expected = _make_txn_out(tags=["lunch", "work"])
    mock_repo_cls.return_value.create.return_value = expected

    uc = AddTransaction(uow, svc)
    result = await uc.execute(
        user_id=USER_ID,
        date=date(2026, 3, 7),
        amount=Decimal("42.50"),
        category="food",
        description="lunch",
        transaction_type=TransactionType.expense,
        tags=["lunch", "work"],
    )

    assert result.tags == ["lunch", "work"]


# ── ListTransactions ────────────────────────────────────────────────────


async def test_list_transactions():
    txns = [_make_txn_out(), _make_txn_out(id=uuid4())]
    repo = MagicMock()
    repo.list_by_user.return_value = txns

    uc = ListTransactions(repo)
    result = await uc.execute(USER_ID, limit=10)

    assert len(result) == 2
    repo.list_by_user.assert_called_once_with(
        USER_ID,
        start_date=None,
        end_date=None,
        categories=None,
        txn_type=None,
        limit=10,
        offset=0,
    )


async def test_list_transactions_with_filters():
    repo = MagicMock()
    repo.list_by_user.return_value = []

    uc = ListTransactions(repo)
    await uc.execute(
        USER_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        categories=["food"],
        txn_type="expense",
    )

    repo.list_by_user.assert_called_once_with(
        USER_ID,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        categories=["food"],
        txn_type="expense",
        limit=50,
        offset=0,
    )


# ── SearchTransactions ──────────────────────────────────────────────────


async def test_search_transactions():
    svc = _mock_embedding_svc()
    txn = _make_txn_out()
    repo = MagicMock()
    repo.get_by_ids.return_value = [txn]
    vector_store = MagicMock()
    vector_store.search.return_value = [str(FAKE_ID)]

    uc = SearchTransactions(repo, vector_store, svc)
    result = await uc.execute(USER_ID, "lunch at office")

    assert len(result) == 1
    svc.embed.assert_called_once_with("lunch at office")
    vector_store.search.assert_called_once()
    repo.get_by_ids.assert_called_once()


async def test_search_transactions_no_results():
    svc = _mock_embedding_svc()
    repo = MagicMock()
    vector_store = MagicMock()
    vector_store.search.return_value = []

    uc = SearchTransactions(repo, vector_store, svc)
    result = await uc.execute(USER_ID, "nonexistent")

    assert result == []
    repo.get_by_ids.assert_not_called()


# ── UpdateTransaction ───────────────────────────────────────────────────


@patch("flux_core.use_cases.transactions.update_transaction.SqliteTransactionRepository")
async def test_update_transaction(mock_repo_cls):
    uow = _mock_uow()
    svc = _mock_embedding_svc()
    updated = _make_txn_out(category="dining", description="dinner")
    mock_repo_cls.return_value.update.return_value = updated

    updates = TransactionUpdate(category="dining", description="dinner")
    uc = UpdateTransaction(uow, svc)
    result = await uc.execute(FAKE_ID, USER_ID, updates)

    assert result.category == "dining"
    mock_repo_cls.return_value.update.assert_called_once_with(FAKE_ID, USER_ID, updates)
    svc.embed.assert_called_once_with("dining dinner")
    uow.add_vector.assert_called_once()
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.transactions.update_transaction.SqliteTransactionRepository")
async def test_update_transaction_not_found(mock_repo_cls):
    uow = _mock_uow()
    svc = _mock_embedding_svc()
    mock_repo_cls.return_value.update.return_value = None

    updates = TransactionUpdate(category="dining")
    uc = UpdateTransaction(uow, svc)

    try:
        await uc.execute(FAKE_ID, USER_ID, updates)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert str(FAKE_ID) in str(e)


# ── DeleteTransaction ───────────────────────────────────────────────────


@patch("flux_core.use_cases.transactions.delete_transaction.SqliteTransactionRepository")
async def test_delete_transaction(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.delete.return_value = True

    uc = DeleteTransaction(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result is True
    mock_repo_cls.return_value.delete.assert_called_once_with(FAKE_ID, USER_ID)
    uow.delete_vector.assert_called_once_with("transaction_embeddings", str(FAKE_ID))
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.transactions.delete_transaction.SqliteTransactionRepository")
async def test_delete_transaction_not_found(mock_repo_cls):
    uow = _mock_uow()
    mock_repo_cls.return_value.delete.return_value = False

    uc = DeleteTransaction(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result is False
    uow.delete_vector.assert_not_called()
    uow.add_event.assert_not_called()
    uow.commit.assert_called_once()
