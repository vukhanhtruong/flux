from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
import pytest
from flux_core.tools.transaction_tools import (
    add_transaction,
    list_transactions,
    search_transactions,
    update_transaction,
    delete_transaction,
)
from flux_core.models.transaction import TransactionOut, TransactionType


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.embed.return_value = [0.1] * 384
    return service


@pytest.mark.asyncio
async def test_add_transaction(mock_repo, mock_embedding_service):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = TransactionOut(
        id=test_uuid,
        user_id="test_user",
        date=date(2026, 1, 15),
        amount=Decimal("50.00"),
        category="Food",
        description="Lunch",
        type=TransactionType.expense,
        is_recurring=False,
        tags=["dining"],
        created_at=datetime.now()
    )

    result = await add_transaction(
        user_id="test_user",
        date="2026-01-15",
        amount=50.00,
        category="Food",
        description="Lunch",
        transaction_type="expense",
        is_recurring=False,
        tags=["dining"],
        repo=mock_repo,
        embedding_service=mock_embedding_service
    )

    assert result["id"] == str(test_uuid)
    assert result["amount"] == "50.00"
    mock_repo.create.assert_called_once()
    mock_embedding_service.embed.assert_called_once()


@pytest.mark.asyncio
async def test_list_transactions(mock_repo):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        TransactionOut(
            id=test_uuid,
            user_id="test_user",
            date=date(2026, 1, 15),
            amount=Decimal("50.00"),
            category="Food",
            description="Lunch",
            type=TransactionType.expense,
            is_recurring=False,
            tags=["dining"],
            created_at=datetime.now()
        )
    ]

    result = await list_transactions(
        user_id="test_user",
        limit=10,
        repo=mock_repo
    )

    assert len(result) == 1
    assert result[0]["id"] == str(test_uuid)
    mock_repo.list_by_user.assert_called_once()


@pytest.mark.asyncio
async def test_search_transactions(mock_repo, mock_embedding_service):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.search_by_embedding.return_value = [
        TransactionOut(
            id=test_uuid,
            user_id="test_user",
            date=date(2026, 1, 15),
            amount=Decimal("50.00"),
            category="Food",
            description="Coffee shop",
            type=TransactionType.expense,
            is_recurring=False,
            tags=[],
            created_at=datetime.now()
        )
    ]

    result = await search_transactions(
        user_id="test_user",
        query="coffee",
        limit=5,
        repo=mock_repo,
        embedding_service=mock_embedding_service
    )

    assert len(result) == 1
    assert result[0]["description"] == "Coffee shop"
    mock_embedding_service.embed.assert_called_once_with("coffee")
    mock_repo.search_by_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_update_transaction(mock_repo):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.update.return_value = TransactionOut(
        id=test_uuid,
        user_id="test_user",
        date=date(2026, 1, 15),
        amount=Decimal("75.00"),
        category="Food",
        description="Dinner",
        type=TransactionType.expense,
        is_recurring=False,
        tags=[],
        created_at=datetime.now()
    )

    result = await update_transaction(
        transaction_id=str(test_uuid),
        user_id="test_user",
        amount=75.00,
        description="Dinner",
        repo=mock_repo
    )

    assert result["amount"] == "75.00"
    assert result["description"] == "Dinner"
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_delete_transaction(mock_repo):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.delete.return_value = True

    result = await delete_transaction(
        transaction_id=str(test_uuid),
        user_id="test_user",
        repo=mock_repo
    )

    assert result["success"] is True
    mock_repo.delete.assert_called_once()


@pytest.mark.asyncio
async def test_add_transaction_resolves_today_date(mock_repo, mock_embedding_service):
    """'today' as the date string is normalized to today's ISO date."""
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    today_iso = date.today().isoformat()
    mock_repo.create.return_value = TransactionOut(
        id=test_uuid,
        user_id="test_user",
        date=date.today(),
        amount=Decimal("50.00"),
        category="Food",
        description="Lunch",
        type=TransactionType.expense,
        is_recurring=False,
        tags=[],
        created_at=datetime.now(),
    )

    result = await add_transaction(
        user_id="test_user",
        date="today",
        amount=50.00,
        category="Food",
        description="Lunch",
        transaction_type="expense",
        repo=mock_repo,
        embedding_service=mock_embedding_service,
    )

    # The repo should have been called with a TransactionCreate whose date == today
    create_call_args = mock_repo.create.call_args
    transaction_arg = create_call_args[0][0]
    assert str(transaction_arg.date) == today_iso


@pytest.mark.asyncio
async def test_add_transaction_resolves_yesterday_date(mock_repo, mock_embedding_service):
    """'yesterday' as the date string is normalized to yesterday's ISO date."""
    from datetime import timedelta
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    yesterday = date.today() - timedelta(days=1)
    mock_repo.create.return_value = TransactionOut(
        id=test_uuid,
        user_id="test_user",
        date=yesterday,
        amount=Decimal("30.00"),
        category="Transport",
        description="Taxi",
        type=TransactionType.expense,
        is_recurring=False,
        tags=[],
        created_at=datetime.now(),
    )

    result = await add_transaction(
        user_id="test_user",
        date="yesterday",
        amount=30.00,
        category="Transport",
        description="Taxi",
        transaction_type="expense",
        repo=mock_repo,
        embedding_service=mock_embedding_service,
    )

    create_call_args = mock_repo.create.call_args
    transaction_arg = create_call_args[0][0]
    assert str(transaction_arg.date) == yesterday.isoformat()
