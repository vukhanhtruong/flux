---
paths:
  - "packages/core/**/*.py"
  - "packages/api-server/**/*.py"
  - "packages/mcp-server/**/*.py"
  - "packages/agent-bot/**/*.py"
---

# Python Backend Patterns

## Use Case Pattern

Every business operation is a Use Case class with an `execute()` method.

```python
# Write use case (with UoW)
class AddTransaction:
    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider): ...
    async def execute(self, user_id, date, amount, ...) -> Transaction: ...

# Read-only use case (no UoW)
class SearchTransactions:
    def __init__(self, txn_repo, embedding_repo, embedding_svc): ...
    async def execute(self, user_id, query, limit) -> list[Transaction]: ...
```

## Unit of Work Pattern

ALL write operations go through UnitOfWork. It coordinates:
1. SQLite transaction (BEGIN/COMMIT/ROLLBACK)
2. zvec writes (only if embeddings registered via `add_vector()`)
3. Event emission (only after both stores succeed)

```python
async with uow:
    uow.transactions.create(txn)
    uow.add_vector("transactions", str(txn.id), embedding, metadata)
    uow.add_event(TransactionCreated(...))
    await uow.commit()
```

## Repository Pattern

- **Interfaces** in `repositories/` — Protocol classes defining method signatures
- **Implementations** in `sqlite/` — pure SQL, take `sqlite3.Connection` from UoW
- Repos accept and return Pydantic models at the interface boundary
- Repos never know about zvec or events — that's the UoW's job

## EventBus Pattern

In-process async pub/sub:
- Subscribers are `async` callables
- One subscriber failure doesn't block others (error logged, continues)
- Events emitted only after successful UoW commit

## SQL Safety

- **All SQL uses parameterized queries** via sqlite3 (`?` placeholders) — never string interpolation
- **Financial amounts** are `Decimal` in Python, stored as `TEXT` in SQLite for precision
- **Every table has `user_id`** — supports multi-user via messaging platform user IDs (e.g., `tg:12345`)

## Database Configuration

- WAL mode for concurrent reads, serialized writes
- `synchronous=NORMAL` for performance
- `busy_timeout=5000`
- `cache_size=8MB`
