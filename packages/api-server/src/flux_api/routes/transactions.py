"""Transaction REST routes — thin adapters over use cases."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, status

from flux_api.deps import get_db, get_embedding_service, get_uow, get_vector_store
from flux_core.models.transaction import TransactionOut, TransactionType, TransactionUpdate
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.use_cases.transactions.add_transaction import AddTransaction
from flux_core.use_cases.transactions.delete_transaction import DeleteTransaction
from flux_core.use_cases.transactions.list_transactions import ListTransactions
from flux_core.use_cases.transactions.search_transactions import SearchTransactions
from flux_core.use_cases.transactions.update_transaction import UpdateTransaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_transaction(
    user_id: str,
    date_str: str,
    amount: float,
    category: str,
    description: str,
    transaction_type: str,
    is_recurring: bool = False,
    tags: list[str] | None = None,
) -> TransactionOut:
    """Add a new transaction."""
    uc = AddTransaction(get_uow(), get_embedding_service())
    return await uc.execute(
        user_id,
        date.fromisoformat(date_str),
        Decimal(str(amount)),
        category,
        description,
        TransactionType(transaction_type),
        is_recurring=is_recurring,
        tags=tags,
    )


@router.get("/")
async def list_transactions(
    user_id: str,
    limit: int = 50,
    start_date: str | None = None,
    end_date: str | None = None,
    categories: list[str] | None = None,
    transaction_type: str | None = None,
) -> list[TransactionOut]:
    """List transactions for a user."""
    db = get_db()
    repo = SqliteTransactionRepository(db.connection())
    uc = ListTransactions(repo)
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    return await uc.execute(
        user_id, start_date=sd, end_date=ed,
        categories=categories, txn_type=transaction_type, limit=limit,
    )


@router.get("/search")
async def search_transactions(
    user_id: str,
    query: str,
    limit: int = 10,
) -> list[TransactionOut]:
    """Search transactions semantically."""
    db = get_db()
    repo = SqliteTransactionRepository(db.connection())
    uc = SearchTransactions(repo, get_vector_store(), get_embedding_service())
    return await uc.execute(user_id, query, limit=limit)


@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    user_id: str,
) -> TransactionOut:
    """Get a transaction by ID."""
    db = get_db()
    repo = SqliteTransactionRepository(db.connection())
    txn = repo.get_by_id(UUID(transaction_id), user_id)
    if txn is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.patch("/{transaction_id}")
async def update_transaction(
    transaction_id: str,
    user_id: str,
    updates: TransactionUpdate,
) -> TransactionOut:
    """Update a transaction."""
    uc = UpdateTransaction(get_uow(), get_embedding_service())
    return await uc.execute(UUID(transaction_id), user_id, updates)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    user_id: str,
) -> None:
    """Delete a transaction."""
    uc = DeleteTransaction(get_uow())
    await uc.execute(UUID(transaction_id), user_id)
