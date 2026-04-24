"""Subscription tools for the deepagents runner.

Each tool wraps an existing ``flux_core`` Use Case with ``user_id`` closed
over. The model sees these tools and never sees ``user_id`` as an argument,
so cross-user queries are structurally impossible.

Mirrors the MCP-side surface in
``packages/mcp-server/src/flux_mcp/tools/financial_tools.py`` — the shape
of tool inputs/outputs is intentionally identical so the model experiences
the same contract regardless of host.
"""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from langchain_core.tools import BaseTool, StructuredTool

from flux_core.models.subscription import BillingCycle
from flux_core.sqlite.subscription_repo import SqliteSubscriptionRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.subscriptions.create_subscription import CreateSubscription
from flux_core.use_cases.subscriptions.delete_subscription import DeleteSubscription
from flux_core.use_cases.subscriptions.list_subscriptions import ListSubscriptions
from flux_core.use_cases.subscriptions.toggle_subscription import ToggleSubscription

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database


def build_subscription_tools(*, user_id: str, db: Database) -> list[BaseTool]:
    """Return the subscription tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
    """

    async def create_subscription(
        name: str,
        amount: str,
        billing_cycle: str,
        next_date: str,
        category: str,
    ) -> dict:
        """Create a new recurring subscription (e.g. Netflix, Spotify).

        Args:
            name: Service name (e.g. "Netflix", "Google One").
            amount: Decimal string for the billing amount, e.g. "9.99".
            billing_cycle: "monthly" or "yearly".
            next_date: Next billing date in YYYY-MM-DD format.
            category: Spending category (e.g. "entertainment", "software").

        Returns:
            Dict with id, name, amount, billing_cycle, next_date, category,
            active.
        """
        uow = UnitOfWork(db)
        uc = CreateSubscription(uow)
        result = await uc.execute(
            user_id,
            name,
            Decimal(amount),
            BillingCycle(billing_cycle),
            date_cls.fromisoformat(next_date),
            category,
        )
        return {
            "id": str(result.id),
            "name": result.name,
            "amount": str(result.amount),
            "billing_cycle": result.billing_cycle.value,
            "next_date": str(result.next_date),
            "category": result.category,
            "active": result.active,
        }

    async def list_subscriptions(active_only: bool = True) -> list[dict]:
        """List subscriptions for the current user.

        Args:
            active_only: If True (default), return only active subscriptions.
                Pass False to include archived/inactive subscriptions.

        Returns:
            List of dicts, each with id, name, amount, billing_cycle,
            next_date, category, active.
        """
        repo = SqliteSubscriptionRepository(db.connection())
        uc = ListSubscriptions(repo)
        results = await uc.execute(user_id, active_only=active_only)
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "amount": str(s.amount),
                "billing_cycle": s.billing_cycle.value,
                "next_date": str(s.next_date),
                "category": s.category,
                "active": s.active,
            }
            for s in results
        ]

    async def toggle_subscription(subscription_id: str) -> dict:
        """Toggle a subscription active/inactive (archive or restore).

        Args:
            subscription_id: UUID string of the subscription to toggle.

        Returns:
            Dict with id, name, active, next_date.
        """
        uow = UnitOfWork(db)
        uc = ToggleSubscription(uow)
        result = await uc.execute(UUID(subscription_id), user_id)
        return {
            "id": str(result.id),
            "name": result.name,
            "active": result.active,
            "next_date": str(result.next_date),
        }

    async def delete_subscription(subscription_id: str) -> dict:
        """Delete a subscription permanently.

        Args:
            subscription_id: UUID string of the subscription to delete.

        Returns:
            Dict with deleted (bool) and subscription_id.
        """
        uow = UnitOfWork(db)
        uc = DeleteSubscription(uow)
        success = await uc.execute(UUID(subscription_id), user_id)
        return {"deleted": success, "subscription_id": subscription_id}

    return [
        StructuredTool.from_function(
            coroutine=create_subscription,
            name="create_subscription",
            description=create_subscription.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=list_subscriptions,
            name="list_subscriptions",
            description=list_subscriptions.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=toggle_subscription,
            name="toggle_subscription",
            description=toggle_subscription.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=delete_subscription,
            name="delete_subscription",
            description=delete_subscription.__doc__ or "",
        ),
    ]
