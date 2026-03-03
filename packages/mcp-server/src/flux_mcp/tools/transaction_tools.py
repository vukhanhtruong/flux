from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.embeddings.service import EmbeddingProvider
from flux_core.tools import transaction_tools as biz


def register_transaction_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_embedding_service: Callable[[], EmbeddingProvider],
    get_user_id: Callable[[], str],
    get_user_timezone: Callable[[], Awaitable[str]],
):
    @mcp.tool()
    async def add_transaction(
        date: str, amount: float, category: str,
        description: str, transaction_type: str,
        is_recurring: bool = False, tags: list[str] | None = None,
    ) -> dict:
        """Add a new transaction."""
        db = await get_db()
        return await biz.add_transaction(
            get_user_id(), date, amount, category, description,
            transaction_type, TransactionRepository(db), get_embedding_service(),
            is_recurring, tags,
            user_timezone=await get_user_timezone(),
        )

    @mcp.tool()
    async def list_transactions(
        limit: int = 50, start_date: str | None = None, end_date: str | None = None,
        categories: list[str] | None = None, transaction_type: str | None = None,
    ) -> list[dict]:
        """List transactions."""
        db = await get_db()
        return await biz.list_transactions(
            get_user_id(), TransactionRepository(db), limit, start_date, end_date,
            categories, transaction_type,
        )

    @mcp.tool()
    async def search_transactions(query: str, limit: int = 10) -> list[dict]:
        """Search transactions semantically."""
        db = await get_db()
        return await biz.search_transactions(
            get_user_id(), query, TransactionRepository(db), get_embedding_service(), limit,
        )
