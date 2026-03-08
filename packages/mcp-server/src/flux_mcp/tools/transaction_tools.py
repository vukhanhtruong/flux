from datetime import date as date_cls
from decimal import Decimal
from typing import Callable

from fastmcp import FastMCP
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.models.transaction import TransactionType
from flux_core.sqlite.database import Database
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.models.transaction import TransactionUpdate
from flux_core.use_cases.transactions.add_transaction import AddTransaction
from flux_core.use_cases.transactions.delete_transaction import DeleteTransaction
from flux_core.use_cases.transactions.list_transactions import ListTransactions
from flux_core.use_cases.transactions.search_transactions import SearchTransactions
from flux_core.use_cases.transactions.update_transaction import UpdateTransaction
from flux_core.vector.store import ZvecStore


def register_transaction_tools(
    mcp: FastMCP,
    get_db: Callable[[], Database],
    get_uow: Callable[[], UnitOfWork],
    get_vector_store: Callable[[], ZvecStore],
    get_embedding_service: Callable[[], EmbeddingProvider],
    get_user_id: Callable[[], str],
    get_user_timezone: Callable[[], str],
):
    @mcp.tool()
    async def add_transaction(
        date: str, amount: float, category: str,
        description: str, transaction_type: str,
        is_recurring: bool = False, tags: list[str] | None = None,
    ) -> dict:
        """Add a new transaction."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        uc = AddTransaction(get_uow(), get_embedding_service())
        tz = get_user_timezone()

        if date == "today":
            txn_date = datetime.now(ZoneInfo(tz)).date()
        else:
            txn_date = date_cls.fromisoformat(date)

        result = await uc.execute(
            get_user_id(), txn_date, Decimal(str(amount)),
            category, description, TransactionType(transaction_type),
            is_recurring=is_recurring, tags=tags,
        )
        return {
            "id": str(result.id),
            "date": str(result.date),
            "amount": str(result.amount),
            "category": result.category,
            "description": result.description,
            "type": result.type.value,
            "is_recurring": result.is_recurring,
            "tags": result.tags,
        }

    @mcp.tool()
    async def list_transactions(
        limit: int = 50, start_date: str | None = None, end_date: str | None = None,
        categories: list[str] | None = None, transaction_type: str | None = None,
    ) -> list[dict]:
        """List transactions."""
        db = get_db()
        repo = SqliteTransactionRepository(db.connection())
        uc = ListTransactions(repo)
        sd = date_cls.fromisoformat(start_date) if start_date else None
        ed = date_cls.fromisoformat(end_date) if end_date else None
        results = await uc.execute(
            get_user_id(), start_date=sd, end_date=ed,
            categories=categories, txn_type=transaction_type, limit=limit,
        )
        return [
            {
                "id": str(t.id),
                "date": str(t.date),
                "amount": str(t.amount),
                "category": t.category,
                "description": t.description,
                "type": t.type.value,
                "is_recurring": t.is_recurring,
                "tags": t.tags,
            }
            for t in results
        ]

    @mcp.tool()
    async def search_transactions(query: str, limit: int = 10) -> list[dict]:
        """Search transactions semantically."""
        db = get_db()
        repo = SqliteTransactionRepository(db.connection())
        uc = SearchTransactions(repo, get_vector_store(), get_embedding_service())
        results = await uc.execute(get_user_id(), query, limit=limit)
        return [
            {
                "id": str(t.id),
                "date": str(t.date),
                "amount": str(t.amount),
                "category": t.category,
                "description": t.description,
                "type": t.type.value,
            }
            for t in results
        ]

    @mcp.tool()
    async def delete_transaction(transaction_id: str) -> dict:
        """Delete a transaction by ID."""
        from uuid import UUID

        uc = DeleteTransaction(get_uow())
        deleted = await uc.execute(UUID(transaction_id), get_user_id())
        return {"deleted": deleted}

    @mcp.tool()
    async def update_transaction(
        transaction_id: str,
        date: str | None = None,
        amount: float | None = None,
        category: str | None = None,
        description: str | None = None,
        transaction_type: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Update a transaction. Only provided fields are changed."""
        from uuid import UUID

        update_data = {}
        if date is not None:
            update_data["date"] = date_cls.fromisoformat(date)
        if amount is not None:
            update_data["amount"] = Decimal(str(amount))
        if category is not None:
            update_data["category"] = category
        if description is not None:
            update_data["description"] = description
        if transaction_type is not None:
            update_data["type"] = TransactionType(transaction_type)
        if tags is not None:
            update_data["tags"] = tags

        updates = TransactionUpdate(**update_data)
        uc = UpdateTransaction(get_uow(), get_embedding_service())
        result = await uc.execute(UUID(transaction_id), get_user_id(), updates)
        return {
            "id": str(result.id),
            "date": str(result.date),
            "amount": str(result.amount),
            "category": result.category,
            "description": result.description,
            "type": result.type.value,
            "is_recurring": result.is_recurring,
            "tags": result.tags,
        }
