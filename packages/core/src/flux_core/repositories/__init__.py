"""Repository Protocol interfaces for all domains."""

from flux_core.repositories.asset_repo import AssetRepository
from flux_core.repositories.budget_repo import BudgetRepository
from flux_core.repositories.embedding_repo import EmbeddingRepository
from flux_core.repositories.goal_repo import GoalRepository
from flux_core.repositories.memory_repo import MemoryRepository
from flux_core.repositories.subscription_repo import SubscriptionRepository
from flux_core.repositories.transaction_repo import TransactionRepository
from flux_core.repositories.user_repo import UserRepository

__all__ = [
    "AssetRepository",
    "BudgetRepository",
    "EmbeddingRepository",
    "GoalRepository",
    "MemoryRepository",
    "SubscriptionRepository",
    "TransactionRepository",
    "UserRepository",
]
