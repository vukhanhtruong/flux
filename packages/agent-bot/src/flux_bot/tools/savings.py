"""Savings tools for the deepagents runner.

Each tool wraps an existing ``flux_core`` Use Case with ``user_id`` closed
over. The model sees these tools and never sees ``user_id`` as an argument,
so cross-user queries are structurally impossible.

Mirrors the MCP-side surface in
``packages/mcp-server/src/flux_mcp/tools/savings_tools.py`` — the shape
of tool inputs/outputs is intentionally identical so the model experiences
the same contract regardless of host.
"""
from __future__ import annotations

from datetime import UTC, date as date_cls, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from langchain_core.tools import BaseTool, StructuredTool

from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.savings.create_savings import CreateSavings
from flux_core.use_cases.savings.withdraw_savings import WithdrawSavings

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database


def build_savings_tools(*, user_id: str, db: Database) -> list[BaseTool]:
    """Return the savings tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
    """

    async def create_savings(
        name: str,
        amount: str,
        interest_rate: str,
        compound_frequency: str,
        maturity_date: str,
        category: str,
        start_date: str | None = None,
    ) -> dict:
        """Create a new savings deposit with compound interest.

        Before calling this tool, confirm all details with the user
        (name, amount, interest rate, compound frequency, maturity date).

        Args:
            name: Descriptive name for the deposit (e.g. "Fixed Deposit").
            amount: Decimal string for the principal amount, e.g. "10000.00".
            interest_rate: Annual percentage as a decimal string, e.g. "5.0"
                for 5% p.a.
            compound_frequency: One of "monthly", "quarterly", "yearly", or
                "at_maturity". Use "at_maturity" for fixed deposits where
                interest is applied once at the end.
            maturity_date: ISO date (YYYY-MM-DD) when the deposit matures.
            category: Spending category (e.g. "savings", "investments").
            start_date: Optional ISO date (YYYY-MM-DD) for the deposit start.
                Defaults to today if not provided.

        Returns:
            Dict with id, name, amount, interest_rate, compound_frequency,
            next_date, maturity_date, active.
        """
        resolved_start = (
            date_cls.fromisoformat(start_date)
            if start_date
            else datetime.now(UTC).date()
        )
        uow = UnitOfWork(db)
        uc = CreateSavings(uow)
        result = await uc.execute(
            user_id,
            name,
            Decimal(amount),
            Decimal(interest_rate),
            compound_frequency,
            resolved_start,
            date_cls.fromisoformat(maturity_date),
            category,
        )
        return {
            "id": str(result.id),
            "name": result.name,
            "amount": str(result.amount),
            "interest_rate": str(result.interest_rate),
            "compound_frequency": result.compound_frequency,
            "next_date": str(result.next_date),
            "maturity_date": str(result.maturity_date) if result.maturity_date else None,
            "active": result.active,
        }

    async def withdraw_savings(asset_id: str) -> dict:
        """Withdraw a matured savings deposit.

        Creates an income transaction for the full balance and deactivates the
        asset. Money moves from 'asset balance' to 'cash (transactions)'.

        Args:
            asset_id: UUID string of the savings deposit to withdraw.

        Returns:
            Dict with withdrawn_amount, transaction_id, asset_name, asset_id.
        """
        uow = UnitOfWork(db)
        uc = WithdrawSavings(uow)
        return await uc.execute(UUID(asset_id), user_id)

    return [
        StructuredTool.from_function(
            coroutine=create_savings,
            name="create_savings",
            description=create_savings.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=withdraw_savings,
            name="withdraw_savings",
            description=withdraw_savings.__doc__ or "",
        ),
    ]
