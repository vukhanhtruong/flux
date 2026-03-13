"""Test transaction REST routes."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from flux_core.models.transaction import TransactionOut, TransactionType
from flux_core.repositories.transaction_repo import TransactionRepository


@pytest.fixture
def mock_repo():
    """Mock transaction repository."""
    return MagicMock(spec=TransactionRepository)


@pytest.fixture
def mock_db(mock_repo):
    """Mock Database that returns a connection wired to mock_repo."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embed.return_value = [0.1] * 384
    return service


def _make_txn_out(**overrides) -> TransactionOut:
    defaults = dict(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        user_id="user-1",
        date=date(2024, 1, 15),
        amount=Decimal("50.00"),
        category="groceries",
        description="Weekly shopping",
        type=TransactionType.expense,
        is_recurring=False,
        tags=["food"],
        created_at=datetime(2024, 1, 15, 10, 0, 0),
    )
    defaults.update(overrides)
    return TransactionOut(**defaults)


def test_add_transaction(client, mock_uow, mock_embedding_service):
    """Test POST /transactions/ creates a transaction."""
    expected = _make_txn_out()

    with (
        patch("flux_api.routes.transactions.get_uow", return_value=mock_uow),
        patch("flux_api.routes.transactions.get_embedding_service",
              return_value=mock_embedding_service),
        patch(
            "flux_api.routes.transactions.AddTransaction"
        ) as MockUC,
    ):
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=expected)
        MockUC.return_value = mock_uc

        response = client.post(
            "/transactions/",
            params={
                "user_id": "user-1",
                "date_str": "2024-01-15",
                "amount": 50.00,
                "category": "groceries",
                "description": "Weekly shopping",
                "transaction_type": "expense",
                "is_recurring": False,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "12345678-1234-5678-1234-567812345678"
    assert data["user_id"] == "user-1"
    assert data["amount"] == "50.00"
    assert data["category"] == "groceries"


def test_list_transactions(client, mock_repo):
    """Test GET /transactions/ lists user transactions."""
    mock_transactions = [
        _make_txn_out(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            description="Shopping",
            tags=[],
        ),
        _make_txn_out(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            date=date(2024, 1, 20),
            amount=Decimal("1000.00"),
            category="salary",
            description="Paycheck",
            type=TransactionType.income,
            is_recurring=True,
            tags=["monthly"],
        ),
    ]

    with (
        patch("flux_api.routes.transactions.get_db") as mock_get_db,
        patch(
            "flux_api.routes.transactions.SqliteTransactionRepository",
            return_value=mock_repo,
        ),
    ):
        mock_get_db.return_value = MagicMock()
        mock_uc = AsyncMock(return_value=mock_transactions)
        with patch(
            "flux_api.routes.transactions.ListTransactions"
        ) as MockUC:
            MockUC.return_value.execute = mock_uc
            response = client.get("/transactions/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "11111111-1111-1111-1111-111111111111"
    assert data[1]["id"] == "22222222-2222-2222-2222-222222222222"


def test_get_transaction(client, mock_repo):
    """Test GET /transactions/{id} retrieves a transaction."""
    expected = _make_txn_out(id=UUID("33333333-3333-3333-3333-333333333333"))

    with (
        patch("flux_api.routes.transactions.get_db") as mock_get_db,
        patch(
            "flux_api.routes.transactions.SqliteTransactionRepository",
            return_value=mock_repo,
        ),
    ):
        mock_get_db.return_value = MagicMock()
        mock_repo.get_by_id.return_value = expected
        response = client.get(
            "/transactions/33333333-3333-3333-3333-333333333333?user_id=user-1"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "33333333-3333-3333-3333-333333333333"
    assert data["amount"] == "50.00"


def test_get_transaction_not_found(client, mock_repo):
    """Test GET /transactions/{id} returns 404 when not found."""
    with (
        patch("flux_api.routes.transactions.get_db") as mock_get_db,
        patch(
            "flux_api.routes.transactions.SqliteTransactionRepository",
            return_value=mock_repo,
        ),
    ):
        mock_get_db.return_value = MagicMock()
        mock_repo.get_by_id.return_value = None
        response = client.get(
            "/transactions/33333333-3333-3333-3333-333333333333?user_id=user-1"
        )

    assert response.status_code == 404


def test_search_transactions(client, mock_repo, mock_embedding_service):
    """Test GET /transactions/search returns matching transactions."""
    mock_transactions = [_make_txn_out(description="Coffee")]

    with (
        patch("flux_api.routes.transactions.get_db") as mock_get_db,
        patch(
            "flux_api.routes.transactions.SqliteTransactionRepository",
            return_value=mock_repo,
        ),
        patch("flux_api.routes.transactions.get_vector_store") as mock_get_vs,
        patch(
            "flux_api.routes.transactions.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("flux_api.routes.transactions.SearchTransactions") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        mock_get_vs.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(return_value=mock_transactions)
        response = client.get(
            "/transactions/search?user_id=user-1&query=coffee"
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["description"] == "Coffee"


def test_update_transaction(client, mock_uow, mock_embedding_service):
    """Test PATCH /transactions/{id} updates a transaction."""
    expected = _make_txn_out(category="dining")

    with (
        patch("flux_api.routes.transactions.get_uow", return_value=mock_uow),
        patch(
            "flux_api.routes.transactions.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("flux_api.routes.transactions.UpdateTransaction") as MockUC,
    ):
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=expected)
        MockUC.return_value = mock_uc

        response = client.patch(
            "/transactions/12345678-1234-5678-1234-567812345678?user_id=user-1",
            json={"category": "dining"},
        )

    assert response.status_code == 200
    assert response.json()["category"] == "dining"


def test_delete_transaction(client, mock_uow):
    """Test DELETE /transactions/{id} deletes a transaction."""
    with (
        patch("flux_api.routes.transactions.get_uow", return_value=mock_uow),
        patch(
            "flux_api.routes.transactions.DeleteTransaction"
        ) as MockUC,
    ):
        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(return_value=None)
        MockUC.return_value = mock_uc

        response = client.delete(
            "/transactions/33333333-3333-3333-3333-333333333333?user_id=user-1"
        )

    assert response.status_code == 204
