"""Goal use cases."""

from flux_core.use_cases.goals.create_goal import CreateGoal
from flux_core.use_cases.goals.delete_goal import DeleteGoal
from flux_core.use_cases.goals.deposit_to_goal import DepositToGoal
from flux_core.use_cases.goals.list_goals import ListGoals
from flux_core.use_cases.goals.withdraw_from_goal import WithdrawFromGoal

__all__ = [
    "CreateGoal",
    "DeleteGoal",
    "DepositToGoal",
    "ListGoals",
    "WithdrawFromGoal",
]
