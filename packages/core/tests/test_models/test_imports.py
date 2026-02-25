def test_all_models_importable():
    from flux_core.models import (
        TransactionCreate, TransactionOut, TransactionUpdate,
        BudgetSet, BudgetOut,
        GoalCreate, GoalOut, GoalUpdate,
        SubscriptionCreate, SubscriptionOut,
        AssetCreate, AssetOut,
        MemoryCreate, MemoryOut,
    )
    assert TransactionCreate is not None
