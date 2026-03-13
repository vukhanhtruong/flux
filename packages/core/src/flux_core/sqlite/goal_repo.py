"""SQLite implementation of GoalRepository Protocol."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from flux_core.models.goal import GoalCreate, GoalOut, GoalUpdate


class SqliteGoalRepository:
    """SQLite-backed savings goal repository."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, goal: GoalCreate) -> GoalOut:
        goal_id = str(uuid4())
        self._conn.execute(
            """
            INSERT INTO savings_goals (id, user_id, name, target_amount, deadline, color)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                goal_id,
                goal.user_id,
                goal.name,
                str(goal.target_amount),
                goal.deadline.isoformat() if goal.deadline else None,
                goal.color,
            ),
        )
        return GoalOut(
            id=UUID(goal_id),
            user_id=goal.user_id,
            name=goal.name,
            target_amount=goal.target_amount,
            current_amount=Decimal("0"),
            deadline=goal.deadline,
            color=goal.color,
        )

    def get_by_id(self, goal_id: UUID, user_id: str) -> GoalOut | None:
        row = self._conn.execute(
            "SELECT id, user_id, name, target_amount, current_amount, deadline, color "
            "FROM savings_goals WHERE id = ? AND user_id = ?",
            (str(goal_id), user_id),
        ).fetchone()
        return self._from_row(row) if row else None

    def list_by_user(self, user_id: str) -> list[GoalOut]:
        rows = self._conn.execute(
            "SELECT id, user_id, name, target_amount, current_amount, deadline, color "
            "FROM savings_goals WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def update(
        self, goal_id: UUID, user_id: str, updates: GoalUpdate
    ) -> GoalOut | None:
        fields = updates.model_dump(exclude_none=True)
        if not fields:
            return self.get_by_id(goal_id, user_id)

        set_clauses = []
        params: list = []
        for key, value in fields.items():
            if key in ("target_amount", "current_amount"):
                value = str(value)
            elif key == "deadline" and value is not None:
                value = value.isoformat()
            set_clauses.append(f"{key} = ?")
            params.append(value)

        params.extend([str(goal_id), user_id])
        cursor = self._conn.execute(
            f"UPDATE savings_goals SET {', '.join(set_clauses)} "
            f"WHERE id = ? AND user_id = ?",
            tuple(params),
        )
        if cursor.rowcount == 0:
            return None
        return self.get_by_id(goal_id, user_id)

    def deposit(self, goal_id: UUID, user_id: str, amount: Decimal) -> GoalOut | None:
        current = self.get_by_id(goal_id, user_id)
        if current is None:
            return None
        new_amount = current.current_amount + amount
        self._conn.execute(
            "UPDATE savings_goals SET current_amount = ? WHERE id = ? AND user_id = ?",
            (str(new_amount), str(goal_id), user_id),
        )
        return GoalOut(
            id=current.id,
            user_id=current.user_id,
            name=current.name,
            target_amount=current.target_amount,
            current_amount=new_amount,
            deadline=current.deadline,
            color=current.color,
        )

    def withdraw(
        self, goal_id: UUID, user_id: str, amount: Decimal
    ) -> GoalOut | None:
        current = self.get_by_id(goal_id, user_id)
        if current is None:
            return None
        new_amount = max(current.current_amount - amount, Decimal("0"))
        self._conn.execute(
            "UPDATE savings_goals SET current_amount = ? WHERE id = ? AND user_id = ?",
            (str(new_amount), str(goal_id), user_id),
        )
        return GoalOut(
            id=current.id,
            user_id=current.user_id,
            name=current.name,
            target_amount=current.target_amount,
            current_amount=new_amount,
            deadline=current.deadline,
            color=current.color,
        )

    def delete(self, goal_id: UUID, user_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM savings_goals WHERE id = ? AND user_id = ?",
            (str(goal_id), user_id),
        )
        return cursor.rowcount == 1

    @staticmethod
    def _from_row(row: sqlite3.Row) -> GoalOut:
        return GoalOut(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            name=row["name"],
            target_amount=Decimal(row["target_amount"]),
            current_amount=Decimal(row["current_amount"]),
            deadline=date.fromisoformat(row["deadline"]) if row["deadline"] else None,
            color=row["color"],
        )
