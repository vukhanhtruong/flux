# Core Package

Shared business logic for all flux interfaces.

## Structure

```
packages/core/src/flux_core/
├── models/            # Pydantic v2 domain models
├── repositories/      # Protocol interfaces (what repos do)
│   └── bot/           # Bot-specific repo interfaces
├── sqlite/            # SQLite implementations (how repos work)
│   ├── database.py    # Database class (sqlite3 + ThreadPoolExecutor, WAL)
│   ├── migrations/    # Fresh SQLite DDL
│   └── bot/           # Bot-specific SQLite repos
├── vector/            # sqlite-vec implementations
│   └── store.py       # SqliteVecStore (sqlite-vec)
├── use_cases/         # Business logic (one class per operation)
│   ├── transactions/
│   ├── budgets/
│   ├── goals/
│   ├── subscriptions/
│   ├── savings/
│   ├── memory/
│   ├── analytics/
│   └── bot/
├── events/            # In-process event bus (pub/sub)
│   ├── bus.py
│   └── events.py
├── uow/               # Unit of Work (single-transaction coordinator)
│   └── unit_of_work.py
└── embeddings/        # fastembed service
    └── service.py     # all-MiniLM-L6-v2 (384-dim)
```

## Key Patterns

- Repos accept/return Pydantic models at interface boundary
- Repos never know about vectors or events — UoW handles coordination
- Database uses WAL mode, `synchronous=NORMAL`, `busy_timeout=5000`
- Embeddings stored in sqlite-vec tables within the same SQLite DB
- Embeddings: fastembed all-MiniLM-L6-v2 (384-dim vectors)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
```
