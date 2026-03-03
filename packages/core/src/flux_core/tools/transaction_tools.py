from datetime import date as _date, timedelta, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.transaction import TransactionCreate, TransactionUpdate, TransactionType


def _resolve_date(date_str: str, user_timezone: str = "UTC") -> str:
    """Normalize natural-language date strings to ISO format (YYYY-MM-DD)."""
    s = date_str.strip().lower()
    today = datetime.now(ZoneInfo(user_timezone)).date()
    if s in ("today", "hom nay"):
        return today.isoformat()
    if s in ("yesterday", "hom qua"):
        return (today - timedelta(days=1)).isoformat()
    return date_str  # pass through; Pydantic will validate ISO strings


async def add_transaction(
    user_id: str,
    date: str,
    amount: float,
    category: str,
    description: str,
    transaction_type: str,
    repo: TransactionRepository,
    embedding_service: EmbeddingProvider,
    is_recurring: bool = False,
    tags: Optional[list[str]] = None,
    user_timezone: str = "UTC",
) -> dict:
    """Add a new transaction with semantic embedding."""
    transaction = TransactionCreate(
        user_id=user_id,
        date=_resolve_date(date, user_timezone),
        amount=Decimal(str(amount)),
        category=category,
        description=description,
        type=TransactionType(transaction_type),
        is_recurring=is_recurring,
        tags=tags or []
    )

    embedding = embedding_service.embed(f"{category} {description}")
    result = await repo.create(transaction, embedding)

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "date": str(result.date),
        "amount": str(result.amount),
        "category": result.category,
        "description": result.description,
        "type": result.type.value,
        "is_recurring": result.is_recurring,
        "tags": result.tags,
        "created_at": result.created_at.isoformat()
    }


async def list_transactions(
    user_id: str,
    repo: TransactionRepository,
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[list[str]] = None,
    transaction_type: Optional[str] = None
) -> list[dict]:
    """List transactions for a user with optional filters."""
    transactions = await repo.list_by_user(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        txn_type=transaction_type,
        limit=limit
    )

    return [
        {
            "id": str(t.id),
            "user_id": t.user_id,
            "date": str(t.date),
            "amount": str(t.amount),
            "category": t.category,
            "description": t.description,
            "type": t.type.value,
            "is_recurring": t.is_recurring,
            "tags": t.tags,
            "created_at": t.created_at.isoformat()
        }
        for t in transactions
    ]


async def search_transactions(
    user_id: str,
    query: str,
    repo: TransactionRepository,
    embedding_service: EmbeddingProvider,
    limit: int = 10
) -> list[dict]:
    """Search transactions semantically."""
    embedding = embedding_service.embed(query)
    transactions = await repo.search_by_embedding(user_id, embedding, limit)

    return [
        {
            "id": str(t.id),
            "user_id": t.user_id,
            "date": str(t.date),
            "amount": str(t.amount),
            "category": t.category,
            "description": t.description,
            "type": t.type.value,
            "is_recurring": t.is_recurring,
            "tags": t.tags,
            "created_at": t.created_at.isoformat()
        }
        for t in transactions
    ]


async def update_transaction(
    transaction_id: str,
    user_id: str,
    repo: TransactionRepository,
    date: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    transaction_type: Optional[str] = None,
    tags: Optional[list[str]] = None
) -> dict:
    """Update a transaction."""
    update_data = TransactionUpdate(
        date=date,
        amount=Decimal(str(amount)) if amount is not None else None,
        category=category,
        description=description,
        type=TransactionType(transaction_type) if transaction_type else None,
        tags=tags
    )

    result = await repo.update(UUID(transaction_id), user_id, update_data)
    if not result:
        raise ValueError(f"Transaction {transaction_id} not found")

    return {
        "id": str(result.id),
        "user_id": result.user_id,
        "date": str(result.date),
        "amount": str(result.amount),
        "category": result.category,
        "description": result.description,
        "type": result.type.value,
        "is_recurring": result.is_recurring,
        "tags": result.tags,
        "created_at": result.created_at.isoformat()
    }


async def delete_transaction(
    transaction_id: str,
    user_id: str,
    repo: TransactionRepository
) -> dict:
    """Delete a transaction."""
    success = await repo.delete(UUID(transaction_id), user_id)
    return {"success": success}
