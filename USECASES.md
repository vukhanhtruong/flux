# Use Cases

Living document — all use cases implemented in FluxFinance. Keep in sync with implementation.

---

## Inventory

| Domain            | Use Case               | Writes            | Vectors       | Events                 |
| ----------------- | ---------------------- | ----------------- | ------------- | ---------------------- |
| **Transactions**  | `AddTransaction`       | SQLite            | zvec          | `TransactionCreated`   |
|                   | `ListTransactions`     | —                 | —             | —                      |
|                   | `SearchTransactions`   | —                 | zvec (read)   | —                      |
|                   | `UpdateTransaction`    | SQLite            | zvec          | `TransactionUpdated`   |
|                   | `DeleteTransaction`    | SQLite            | zvec (delete) | `TransactionDeleted`   |
| **Budgets**       | `SetBudget`            | SQLite            | —             | —                      |
|                   | `ListBudgets`          | —                 | —             | —                      |
|                   | `RemoveBudget`         | SQLite            | —             | —                      |
| **Goals**         | `CreateGoal`           | SQLite            | —             | —                      |
|                   | `ListGoals`            | —                 | —             | —                      |
|                   | `DepositToGoal`        | SQLite            | —             | —                      |
|                   | `WithdrawFromGoal`     | SQLite            | —             | —                      |
|                   | `DeleteGoal`           | SQLite            | —             | —                      |
| **Subscriptions** | `CreateSubscription`   | SQLite (2 tables) | —             | `SubscriptionCreated`  |
|                   | `ListSubscriptions`    | —                 | —             | —                      |
|                   | `ToggleSubscription`   | SQLite (2 tables) | —             | —                      |
|                   | `DeleteSubscription`   | SQLite (2 tables) | —             | —                      |
| **Savings**       | `CreateSavings`        | SQLite (2 tables) | —             | `SavingsCreated`       |
|                   | `ProcessInterest`      | SQLite            | —             | —                      |
|                   | `WithdrawSavings`      | SQLite (3 tables) | —             | —                      |
| **Memory**        | `Remember`             | SQLite            | zvec          | `MemoryCreated`        |
|                   | `Recall`               | —                 | zvec (read)   | —                      |
|                   | `ListMemories`         | —                 | —             | —                      |
| **Analytics**     | `GetSummary`           | —                 | —             | —                      |
|                   | `GetTrends`            | —                 | —             | —                      |
|                   | `GetCategoryBreakdown` | —                 | —             | —                      |
| **Bot**           | `ProcessMessage`       | SQLite (3 tables) | —             | `OutboundCreated`      |
|                   | `SendOutbound`         | SQLite            | —             | —                      |
|                   | `CreateScheduledTask`  | SQLite            | —             | `ScheduledTaskCreated` |
|                   | `FireScheduledTask`    | SQLite (2 tables) | —             | `MessageCreated`       |

---

## Backup

| Use Case | Write | Vector | Event | Description |
|---|---|---|---|---|
| CreateBackup | No | No | No | Snapshot SQLite + zvec → .zip → upload to local/S3 |
| RestoreBackup | Yes* | Yes* | No | Auto-backup → download → replace SQLite + zvec |
| ListBackups | No | No | No | List backups from local + S3 |
| DeleteBackup | No | No | No | Delete backup from specified storage |

*RestoreBackup replaces the entire database, bypassing UoW.

---

## Patterns

### Write use cases (with UoW)

```python
class AddTransaction:
    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider): ...
    async def execute(self, user_id, date, amount, ...) -> Transaction:
        # 1. Build domain model
        # 2. Generate embedding
        # 3. UoW: repo.create() + add_vector() + add_event()
        # 4. uow.commit() → SQLite + zvec + events
```

### Read-only use cases (no UoW)

```python
class SearchTransactions:
    def __init__(self, txn_repo, embedding_repo, embedding_svc): ...
    async def execute(self, user_id, query, limit) -> list[Transaction]:
        # 1. Embed query
        # 2. Search zvec for matching IDs
        # 3. Fetch full records from SQLite
```

### SQLite-only write use cases

```python
class CreateScheduledTask:
    def __init__(self, uow: UnitOfWork): ...
    async def execute(self, user_id, prompt, ...) -> ScheduledTask:
        # 1. Build domain model
        # 2. UoW: repo.create() + add_event()
        # 3. uow.commit() → SQLite + events (no zvec)
```

---

## File Locations

```
packages/core/src/flux_core/use_cases/
├── transactions/
│   ├── add_transaction.py
│   ├── list_transactions.py
│   ├── search_transactions.py
│   ├── update_transaction.py
│   └── delete_transaction.py
├── budgets/
│   ├── set_budget.py
│   ├── list_budgets.py
│   └── remove_budget.py
├── goals/
│   ├── create_goal.py
│   ├── list_goals.py
│   ├── deposit_to_goal.py
│   ├── withdraw_from_goal.py
│   └── delete_goal.py
├── subscriptions/
│   ├── create_subscription.py
│   ├── list_subscriptions.py
│   ├── toggle_subscription.py
│   └── delete_subscription.py
├── savings/
│   ├── create_savings.py
│   ├── process_interest.py
│   └── withdraw_savings.py
├── memory/
│   ├── remember.py
│   ├── recall.py
│   └── list_memories.py
├── analytics/
│   ├── get_summary.py
│   ├── get_trends.py
│   └── get_category_breakdown.py
├── bot/
│   ├── process_message.py
│   ├── send_outbound.py
│   ├── create_scheduled_task.py
│   └── fire_scheduled_task.py
└── backup/
    ├── create_backup.py
    ├── restore_backup.py
    ├── list_backups.py
    └── delete_backup.py
```
