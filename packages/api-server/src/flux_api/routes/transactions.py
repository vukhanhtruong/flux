"""Transaction REST routes."""
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from flux_api.deps import get_db, get_embedding_service
from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.embeddings.service import EmbeddingService
from flux_core.models.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionType,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_transaction(
    transaction: TransactionCreate,
    db: Annotated[Database, Depends(get_db)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> TransactionOut:
    """Add a new transaction."""
    repo = TransactionRepository(db)

    # Generate embedding for semantic search
    embedding = None
    if transaction.description:
        embedding = embedding_service.embed_text(transaction.description)

    # Create transaction
    created = await repo.create(transaction, embedding=embedding)

    return created


@router.get("/")
async def list_transactions(
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
    limit: int = 50,
) -> list[TransactionOut]:
    """List transactions for a user."""
    repo = TransactionRepository(db)
    transactions = await repo.list_by_user(user_id, limit=limit)
    return transactions


@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> TransactionOut:
    """Get a transaction by ID."""
    repo = TransactionRepository(db)
    transaction = await repo.get_by_id(UUID(transaction_id), user_id)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    user_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> None:
    """Delete a transaction."""
    repo = TransactionRepository(db)
    await repo.delete(UUID(transaction_id), user_id)
