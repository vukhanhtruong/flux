"""Test transaction REST routes."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app
from flux_api.deps import get_db, get_embedding_service
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.models.transaction import TransactionOut, TransactionType


@pytest.fixture
def mock_repo():
    """Mock transaction repository."""
    repo = AsyncMock(spec=TransactionRepository)
    return repo


@pytest.fixture
def mock_db():
    """Mock database connection."""
    return MagicMock()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embed_text.return_value = [0.1] * 384  # Mock embedding vector
    return service


@pytest.fixture
def client(mock_db, mock_embedding_service):
    """Test client with mocked dependencies."""
    async def override_get_db():
        yield mock_db

    def override_get_embedding_service():
        return mock_embedding_service

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = override_get_embedding_service

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


def test_add_transaction(client, mock_repo):
    """Test POST /transactions/ creates a transaction."""
    mock_transaction = TransactionOut(
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
    mock_repo.create.return_value = mock_transaction

    with patch(
        "flux_api.routes.transactions.TransactionRepository",
        return_value=mock_repo,
    ):
        response = client.post(
            "/transactions/",
            json={
                "user_id": "user-1",
                "date": "2024-01-15",
                "amount": 50.00,
                "category": "groceries",
                "description": "Weekly shopping",
                "type": "expense",
                "is_recurring": False,
                "tags": ["food"],
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
        TransactionOut(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            user_id="user-1",
            date=date(2024, 1, 15),
            amount=Decimal("50.00"),
            category="groceries",
            description="Shopping",
            type=TransactionType.expense,
            is_recurring=False,
            tags=[],
            created_at=datetime(2024, 1, 15, 10, 0, 0),
        ),
        TransactionOut(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            user_id="user-1",
            date=date(2024, 1, 20),
            amount=Decimal("1000.00"),
            category="salary",
            description="Paycheck",
            type=TransactionType.income,
            is_recurring=True,
            tags=["monthly"],
            created_at=datetime(2024, 1, 20, 9, 0, 0),
        ),
    ]
    mock_repo.list_by_user.return_value = mock_transactions

    with patch(
        "flux_api.routes.transactions.TransactionRepository",
        return_value=mock_repo,
    ):
        response = client.get("/transactions/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "11111111-1111-1111-1111-111111111111"
    assert data[1]["id"] == "22222222-2222-2222-2222-222222222222"


def test_get_transaction(client, mock_repo):
    """Test GET /transactions/{id} retrieves a transaction."""
    mock_transaction = TransactionOut(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        user_id="user-1",
        date=date(2024, 1, 15),
        amount=Decimal("50.00"),
        category="groceries",
        description="Shopping",
        type=TransactionType.expense,
        is_recurring=False,
        tags=[],
        created_at=datetime(2024, 1, 15, 10, 0, 0),
    )
    mock_repo.get_by_id.return_value = mock_transaction

    with patch(
        "flux_api.routes.transactions.TransactionRepository",
        return_value=mock_repo,
    ):
        response = client.get("/transactions/33333333-3333-3333-3333-333333333333?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "33333333-3333-3333-3333-333333333333"
    assert data["amount"] == "50.00"


def test_delete_transaction(client, mock_repo):
    """Test DELETE /transactions/{id} deletes a transaction."""
    mock_repo.delete.return_value = True

    with patch(
        "flux_api.routes.transactions.TransactionRepository",
        return_value=mock_repo,
    ):
        response = client.delete("/transactions/33333333-3333-3333-3333-333333333333?user_id=user-1")

    assert response.status_code == 204
    from uuid import UUID
    mock_repo.delete.assert_called_once_with(UUID("33333333-3333-3333-3333-333333333333"), "user-1")
