def test_all_db_importable():
    from flux_core.db import (
        Database, TransactionRepository, BudgetRepository,
        GoalRepository, SubscriptionRepository, AssetRepository,
        MemoryRepository,
    )
    assert Database is not None
