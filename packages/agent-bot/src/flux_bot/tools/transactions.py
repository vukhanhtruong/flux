"""Transaction tools for the deepagents runner.

Each tool wraps an existing ``flux_core`` Use Case with ``user_id`` closed
over. The model sees these tools and never sees ``user_id`` as an
argument, so cross-user queries are structurally impossible.

Mirrors the MCP-side surface in
``packages/mcp-server/src/flux_mcp/tools/transaction_tools.py`` — the
shape of tool inputs/outputs is intentionally identical so the model
experiences the same contract regardless of host.
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from langchain_core.tools import BaseTool, StructuredTool

from flux_core.models.transaction import TransactionType
from flux_core.sqlite.transaction_repo import SqliteTransactionRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.transactions.add_transaction import AddTransaction
from flux_core.use_cases.transactions.list_transactions import ListTransactions
from flux_core.use_cases.transactions.search_transactions import SearchTransactions

if TYPE_CHECKING:
    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.sqlite.database import Database
    from flux_core.vector.store import ZvecStore


# Lazy process-level singletons. Instantiating EmbeddingService downloads
# the fastembed model (~100MB), so production callers should share one
# instance across requests. Tests inject their own fakes.
_default_embedding_svc: EmbeddingProvider | None = None


def _get_default_embedding_svc() -> EmbeddingProvider:
    global _default_embedding_svc
    if _default_embedding_svc is None:
        from flux_core.embeddings.service import EmbeddingService

        _default_embedding_svc = EmbeddingService()
    return _default_embedding_svc


def build_transaction_tools(
    *,
    user_id: str,
    db: Database,
    vector_store: ZvecStore,
    embedding_svc: EmbeddingProvider | None = None,
) -> list[BaseTool]:
    """Return the transaction tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
        vector_store: ``ZvecStore`` used for embedding dual-writes and
            semantic search.
        embedding_svc: Optional ``EmbeddingProvider``. If omitted, a
            process-level ``EmbeddingService`` is lazily constructed
            and reused across calls.
    """
    emb = embedding_svc if embedding_svc is not None else _get_default_embedding_svc()

    async def add_transaction(
        date: str,
        amount: str,
        category: str,
        description: str,
        transaction_type: str,
        is_recurring: bool = False,
        tags: list[str] | None = None,
    ) -> dict:
        """Record a new transaction for the current user.

        Args:
            date: ISO date (YYYY-MM-DD) or the literal string "today" to
                use the user's current local date.
            amount: Decimal string, e.g. "12.50". Must be > 0.
            category: Short category name (e.g. "food", "transport").
            description: Free-text note shown to the user.
            transaction_type: "expense" or "income".
            is_recurring: Mark as recurring (defaults to False).
            tags: Optional list of tag strings.

        Returns:
            Dict with id, date, amount, category, description, type,
            is_recurring, tags.
        """
        if date == "today":
            # Use UTC as a safe default; per-user timezones are resolved
            # upstream in Phase 3 when profile lookup is wired in.
            txn_date = datetime.now(ZoneInfo("UTC")).date()
        else:
            txn_date = date_cls.fromisoformat(date)

        uow = UnitOfWork(db)
        uc = AddTransaction(uow, emb)
        result = await uc.execute(
            user_id=user_id,
            date=txn_date,
            amount=Decimal(amount),
            category=category,
            description=description,
            transaction_type=TransactionType(transaction_type),
            is_recurring=is_recurring,
            tags=tags,
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

    async def list_transactions(
        limit: int = 50,
        start_date: str | None = None,
        end_date: str | None = None,
        categories: list[str] | None = None,
        transaction_type: str | None = None,
    ) -> list[dict]:
        """List recent transactions for the current user.

        Args:
            limit: Max rows to return (default 50).
            start_date: Optional ISO date lower bound (inclusive).
            end_date: Optional ISO date upper bound (inclusive).
            categories: Optional list of category names to filter on.
            transaction_type: Optional "expense" or "income".

        Returns:
            List of dicts, each with the same shape as the
            ``add_transaction`` result, ordered newest first.
        """
        repo = SqliteTransactionRepository(db.connection())
        uc = ListTransactions(repo)
        sd = date_cls.fromisoformat(start_date) if start_date else None
        ed = date_cls.fromisoformat(end_date) if end_date else None
        results = await uc.execute(
            user_id,
            start_date=sd,
            end_date=ed,
            categories=categories,
            txn_type=transaction_type,
            limit=limit,
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

    async def search_transactions(query: str, limit: int = 10) -> list[dict]:
        """Semantic search over the current user's transactions.

        Matches are ranked by vector similarity against the
        category+description of each stored transaction.

        Args:
            query: Natural-language query (e.g. "coffee last week").
            limit: Max matches to return (default 10).

        Returns:
            List of matching transaction dicts (id, date, amount,
            category, description, type).
        """
        repo = SqliteTransactionRepository(db.connection())
        uc = SearchTransactions(repo, vector_store, emb)
        results = await uc.execute(user_id, query, limit=limit)
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

    return [
        StructuredTool.from_function(
            coroutine=add_transaction,
            name="add_transaction",
            description=add_transaction.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=list_transactions,
            name="list_transactions",
            description=list_transactions.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=search_transactions,
            name="search_transactions",
            description=search_transactions.__doc__ or "",
        ),
    ]
