"""Goal tools for the deepagents runner.

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

from flux_core.sqlite.goal_repo import SqliteGoalRepository
from flux_core.uow.unit_of_work import UnitOfWork
from flux_core.use_cases.goals.create_goal import CreateGoal
from flux_core.use_cases.goals.delete_goal import DeleteGoal
from flux_core.use_cases.goals.deposit_to_goal import DepositToGoal
from flux_core.use_cases.goals.list_goals import ListGoals
from flux_core.use_cases.goals.withdraw_from_goal import WithdrawFromGoal

if TYPE_CHECKING:
    from flux_core.sqlite.database import Database


def build_goal_tools(*, user_id: str, db: Database) -> list[BaseTool]:
    """Return the goal tool set bound to a specific user.

    Args:
        user_id: The user identity closed over by every tool. Never
            exposed as a tool argument — guarantees isolation.
        db: Connected core ``Database`` (SQLite, WAL mode).
    """

    async def create_goal(
        name: str,
        target_amount: str,
        deadline: str | None = None,
        color: str = "#3B82F6",
    ) -> dict:
        """Create a new savings goal.

        Args:
            name: Descriptive name for the goal (e.g. "Vacation Fund").
            target_amount: Decimal string for the savings target, e.g.
                "3000.00". Must be > 0.
            deadline: Optional ISO date (YYYY-MM-DD) target completion date.
            color: Optional hex color for UI display (default "#3B82F6").

        Returns:
            Dict with id, name, target_amount, current_amount, deadline,
            color.
        """
        dl = date_cls.fromisoformat(deadline) if deadline else None
        uow = UnitOfWork(db)
        uc = CreateGoal(uow)
        result = await uc.execute(
            user_id,
            name,
            Decimal(target_amount),
            deadline=dl,
            color=color,
        )
        return {
            "id": str(result.id),
            "name": result.name,
            "target_amount": str(result.target_amount),
            "current_amount": str(result.current_amount),
            "deadline": str(result.deadline) if result.deadline else None,
            "color": result.color,
        }

    async def list_goals() -> list[dict]:
        """List all savings goals for the current user.

        Returns:
            List of dicts, each with id, name, target_amount, current_amount,
            deadline, color.
        """
        repo = SqliteGoalRepository(db.connection())
        uc = ListGoals(repo)
        results = await uc.execute(user_id)
        return [
            {
                "id": str(g.id),
                "name": g.name,
                "target_amount": str(g.target_amount),
                "current_amount": str(g.current_amount),
                "deadline": str(g.deadline) if g.deadline else None,
                "color": g.color,
            }
            for g in results
        ]

    async def deposit_to_goal(goal_id: str, amount: str) -> dict:
        """Deposit money into a savings goal.

        Args:
            goal_id: UUID string of the goal to deposit into.
            amount: Decimal string amount to add, e.g. "200.00". Must be > 0.

        Returns:
            Updated goal dict with id, name, target_amount, current_amount,
            deadline, color. Returns an error dict if the goal is not found.
        """
        uow = UnitOfWork(db)
        uc = DepositToGoal(uow)
        try:
            result = await uc.execute(UUID(goal_id), user_id, Decimal(amount))
        except ValueError as e:
            return {"error": str(e)}
        return {
            "id": str(result.id),
            "name": result.name,
            "target_amount": str(result.target_amount),
            "current_amount": str(result.current_amount),
            "deadline": str(result.deadline) if result.deadline else None,
            "color": result.color,
        }

    async def withdraw_from_goal(goal_id: str, amount: str) -> dict:
        """Withdraw money from a savings goal.

        Args:
            goal_id: UUID string of the goal to withdraw from.
            amount: Decimal string amount to remove, e.g. "100.00".
                Must be > 0 and <= current_amount.

        Returns:
            Updated goal dict with id, name, target_amount, current_amount,
            deadline, color. Returns an error dict if the goal is not found
            or amount exceeds balance.
        """
        uow = UnitOfWork(db)
        uc = WithdrawFromGoal(uow)
        try:
            result = await uc.execute(UUID(goal_id), user_id, Decimal(amount))
        except ValueError as e:
            return {"error": str(e)}
        return {
            "id": str(result.id),
            "name": result.name,
            "target_amount": str(result.target_amount),
            "current_amount": str(result.current_amount),
            "deadline": str(result.deadline) if result.deadline else None,
            "color": result.color,
        }

    async def delete_goal(goal_id: str) -> dict:
        """Delete a savings goal permanently.

        Args:
            goal_id: UUID string of the goal to delete.

        Returns:
            Dict with deleted (bool) and goal_id.
        """
        uow = UnitOfWork(db)
        uc = DeleteGoal(uow)
        success = await uc.execute(UUID(goal_id), user_id)
        return {"deleted": success, "goal_id": goal_id}

    return [
        StructuredTool.from_function(
            coroutine=create_goal,
            name="create_goal",
            description=create_goal.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=list_goals,
            name="list_goals",
            description=list_goals.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=deposit_to_goal,
            name="deposit_to_goal",
            description=deposit_to_goal.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=withdraw_from_goal,
            name="withdraw_from_goal",
            description=withdraw_from_goal.__doc__ or "",
        ),
        StructuredTool.from_function(
            coroutine=delete_goal,
            name="delete_goal",
            description=delete_goal.__doc__ or "",
        ),
    ]
