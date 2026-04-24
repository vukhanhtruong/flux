"""LangChain tools for the deepagents runner.

This package mirrors the MCP server's tool surface but runs in-process:
each tool wraps a flux_core Use Case with ``user_id`` closed over, so the
model literally cannot query another user's data.

Domain modules land here incrementally; see the Phase 2 plan for the full
roster. The ``build_tools`` assembler aggregates all domain builders.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

from .analytics import build_analytics_tools
from .bot import build_bot_tools
from .budgets import build_budget_tools
from .goals import build_goal_tools
from .memory import build_memory_tools
from .savings import build_savings_tools
from .subscriptions import build_subscription_tools
from .transactions import build_transaction_tools

if TYPE_CHECKING:
    from flux_core.embeddings.service import EmbeddingProvider
    from flux_core.sqlite.database import Database
    from flux_core.vector.store import ZvecStore


def build_tools(
    *,
    user_id: str,
    db: Database,
    vector_store: ZvecStore | None = None,
    embedding_svc: EmbeddingProvider | None = None,
    **kwargs,
) -> list[BaseTool]:
    """Return all domain tools bound to user_id.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
        vector_store: ``ZvecStore`` used for transaction and memory embedding
            dual-writes and semantic search. Required for tools that perform
            vector operations (transactions, memory).
        embedding_svc: Optional ``EmbeddingProvider``. Falls back to a
            lazily-constructed process-level singleton if omitted.

    Returns:
        Flat list of all domain tools ready for use with a LangChain agent.
    """
    return [
        *build_transaction_tools(
            user_id=user_id,
            db=db,
            vector_store=vector_store,
            embedding_svc=embedding_svc,
        ),
        *build_budget_tools(user_id=user_id, db=db),
        *build_goal_tools(user_id=user_id, db=db),
        *build_memory_tools(
            user_id=user_id,
            db=db,
            vector_store=vector_store,
            embedding_svc=embedding_svc,
        ),
        *build_subscription_tools(user_id=user_id, db=db),
        *build_savings_tools(user_id=user_id, db=db),
        *build_analytics_tools(user_id=user_id, db=db),
        *build_bot_tools(user_id=user_id, db=db),
    ]


__all__ = [
    "build_tools",
    "build_transaction_tools",
    "build_budget_tools",
    "build_goal_tools",
    "build_memory_tools",
    "build_subscription_tools",
    "build_savings_tools",
    "build_analytics_tools",
    "build_bot_tools",
]
