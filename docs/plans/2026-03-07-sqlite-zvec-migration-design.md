# SQLite + zvec Migration Design

**Date:** 2026-03-07
**Status:** Approved
**Branch:** `feature/sqlite-zvec-migration`

---

## Motivation

Replace PostgreSQL + pgvector with SQLite + zvec to enable a local-first, single-container deployment suitable for personal/edge use. No data migration — fresh-start rollout.

## Constraints

- Replace PostgreSQL with SQLite for all relational/stateful data
- Use zvec 0.2.1b0 as the dedicated vector store for embeddings
- Deploy production as one Docker image (pull and run from Docker Hub)
- Fresh-start rollout (no PostgreSQL data migration)
- Strict dual-write: requests fail unless both SQLite and zvec writes succeed
- State behavior changes documented in `STATE-MACHINES.md`

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SQLite concurrency | `sqlite3` + `ThreadPoolExecutor` + WAL mode | Simple, fewer deps than aiosqlite, WAL handles concurrent reads |
| Bot message pipeline | In-process event bus (replaces LISTEN/NOTIFY) | Lower latency than polling, decouples producers/consumers, reusable |
| Embedding model | fastembed `all-MiniLM-L6-v2` (384-dim), in-process | Already lightweight (~50MB RAM), good quality for short financial text |
| Dual-write coordination | Unit of Work pattern | Centralizes atomicity + event emission, single pattern for all writes |
| Repository pattern | Protocol interfaces + SQLite implementations | Tools depend on interfaces, repos are pure SQL, independently testable |
| Business logic | Use Case classes | Self-documenting, one class per operation, clear feature inventory |
| Bot tables | Single SQLite database (core + bot tables) | Single-user, single-container, `bot_` prefix provides namespace separation |
| Dev tooling | `dev.sh` with `uv` venv + hot reload | Single script, fast installs, isolated `.dev-data/` directory |

---

## Architecture

### System Flow

```
Web UI (React) ──HTTP──▶ Nginx ──proxy──▶ FastAPI ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
Claude Desktop ──MCP───▶ FastMCP Server ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
Telegram ──▶ Agent Bot ──▶ Claude SDK ──▶ MCP Server ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec

EventBus (in-process pub/sub) connects:
  - MessageCreated → Dispatcher (replaces Poller)
  - OutboundCreated → OutboundWorker (replaces LISTEN/NOTIFY)
  - TransactionCreated, MemoryCreated → future extensibility
```

### Layering

```
MCP/API (thin adapter)
    ↓
Use Case (business logic + orchestration)
    ↓
Unit of Work (dual-write coordination + event emission)
    ↓
Repository Interface (Protocol)          EventBus (pub/sub)
    ↓                                        ↓
SQLite Implementation    ZvecStore      Subscribers
```

### Package Structure

```
packages/core/src/flux_core/
├── models/                          # UNCHANGED — Pydantic v2
├── repositories/                    # Protocol interfaces
│   ├── transaction_repo.py
│   ├── budget_repo.py
│   ├── goal_repo.py
│   ├── subscription_repo.py
│   ├── asset_repo.py
│   ├── user_repo.py
│   ├── memory_repo.py
│   ├── embedding_repo.py
│   └── bot/
│       ├── message_repo.py
│       ├── session_repo.py
│       ├── scheduled_task_repo.py
│       └── outbound_repo.py
├── sqlite/                          # SQLite implementations
│   ├── database.py                  # Database (sqlite3 + ThreadPoolExecutor, WAL)
│   ├── transaction_repo.py
│   ├── budget_repo.py
│   ├── goal_repo.py
│   ├── subscription_repo.py
│   ├── asset_repo.py
│   ├── user_repo.py
│   ├── memory_repo.py
│   ├── migrations/
│   │   ├── 001_initial.sql
│   │   └── migrate.py
│   └── bot/
│       ├── message_repo.py
│       ├── session_repo.py
│       ├── scheduled_task_repo.py
│       └── outbound_repo.py
├── vector/                          # zvec implementations
│   ├── store.py                     # ZvecStore wrapper
│   └── embedding_repo.py
├── use_cases/                       # Business logic
│   ├── transactions/
│   ├── budgets/
│   ├── goals/
│   ├── subscriptions/
│   ├── savings/
│   ├── memory/
│   ├── analytics/
│   └── bot/
├── events/                          # In-process event bus
│   ├── bus.py
│   └── events.py
├── uow/                            # Unit of Work
│   └── unit_of_work.py
├── tools/                           # Thin MCP/API adapters (simplified)
├── embeddings/                      # UNCHANGED — fastembed
└── db/                              # DELETED — old asyncpg layer
```

---

## Event Bus

### Design

- In-process async pub/sub
- Subscribers are `async` callables
- One subscriber failure doesn't block others (error logged, continues)
- No persistence — fire-and-forget signals
- Thread-safe via asyncio event loop

### Interface

```python
class EventBus(Protocol):
    def subscribe(self, event_type: type[Event], handler: Callable) -> None: ...
    async def emit(self, event: Event) -> None: ...
    def unsubscribe(self, event_type: type[Event], handler: Callable) -> None: ...
```

### Event Types

```python
@dataclass(frozen=True)
class Event:
    timestamp: datetime

class MessageCreated(Event):       # bot_messages INSERT
    message_id: int
    user_id: str

class OutboundCreated(Event):      # bot_outbound_messages INSERT
    outbound_id: int
    user_id: str

class TransactionCreated(Event):   # after UoW commit
    transaction_id: str
    user_id: str

class MemoryCreated(Event):        # after UoW commit
    memory_id: str
    user_id: str

class ScheduledTaskCreated(Event): # scheduler created
    task_id: int
    user_id: str

class ScheduledTaskDue(Event):     # scheduler fires
    task_id: int
    user_id: str
```

### Replaces

| Current (PostgreSQL) | New (EventBus) |
|----------------------|----------------|
| Poller polls `bot_messages` every 2s | `MessageCreated` → Dispatcher |
| `NOTIFY 'new_outbound_message'` trigger | `OutboundCreated` → OutboundWorker |

---

## Unit of Work

### Design

- Universal write pattern — ALL mutations go through UoW
- SQLite transaction wraps all SQL operations
- zvec writes execute after SQLite commit (only if registered)
- Events emitted only after both stores succeed
- Compensating rollback: if zvec fails after SQLite commit, rollback SQLite + cleanup zvec

### Usage Patterns

```python
# Pattern 1: SQLite-only (no embeddings)
async with uow:
    uow.scheduled_tasks.create(task)
    uow.add_event(ScheduledTaskCreated(...))
    await uow.commit()

# Pattern 2: SQLite + zvec (dual-write)
async with uow:
    uow.transactions.create(txn)
    uow.add_vector("transactions", str(txn.id), embedding, metadata)
    uow.add_event(TransactionCreated(...))
    await uow.commit()

# Pattern 3: Multi-table SQLite + event
async with uow:
    uow.subscriptions.create(sub)
    uow.scheduled_tasks.create(task)
    uow.add_event(SubscriptionCreated(...))
    await uow.commit()
```

### Commit Sequence

1. `BEGIN` → execute all SQL → `COMMIT`
2. If pending vectors: execute zvec upserts
3. If zvec fails: rollback SQLite, cleanup zvec docs, raise
4. Emit all pending events
5. Events only fire after both stores succeed

---

## Use Case Pattern

### Structure

Each use case is a class with an `execute()` method:

```python
class AddTransaction:
    def __init__(self, uow: UnitOfWork, embedding_svc: EmbeddingProvider):
        self._uow = uow
        self._embedding_svc = embedding_svc

    async def execute(self, user_id, date, amount, category, description, type) -> Transaction:
        txn = Transaction(...)
        embedding = self._embedding_svc.embed(f"{category} {description}")
        with self._uow:
            self._uow.transactions.create(txn)
            self._uow.add_vector("transactions", str(txn.id), embedding, {...})
            self._uow.add_event(TransactionCreated(...))
            await self._uow.commit()
        return txn
```

Read-only use cases take repos directly, skip UoW:

```python
class SearchTransactions:
    def __init__(self, txn_repo, embedding_repo, embedding_svc):
        ...
    async def execute(self, user_id, query, limit) -> list[Transaction]:
        vector = self._embedding_svc.embed(query)
        doc_ids = self._embedding_repo.search("transactions", vector, limit, filter={"user_id": user_id})
        return self._txn_repo.get_by_ids(doc_ids)
```

Tools layer becomes a thin adapter:

```python
@mcp.tool()
async def add_transaction(user_id, date, amount, ...):
    uc = AddTransaction(get_uow(), get_embedding_svc())
    txn = await uc.execute(user_id, date, Decimal(amount), ...)
    return {"id": str(txn.id), ...}
```

---

## Repository Pattern

### Interface (Protocol)

```python
class TransactionRepository(Protocol):
    def create(self, txn: Transaction) -> Transaction: ...
    def get_by_id(self, txn_id: str, user_id: str) -> Transaction | None: ...
    def get_by_ids(self, ids: list[str]) -> list[Transaction]: ...
    def list_by_user(self, user_id: str, ...) -> list[Transaction]: ...
    def update(self, txn_id: str, user_id: str, **fields) -> Transaction: ...
    def delete(self, txn_id: str, user_id: str) -> bool: ...
```

### Implementation (pure SQL)

```python
class SqliteTransactionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, txn: Transaction) -> Transaction:
        self._conn.execute(
            "INSERT INTO transactions (...) VALUES (?, ?, ?, ...)",
            (str(txn.id), txn.user_id, ...),
        )
        return txn
```

- Repos take a `sqlite3.Connection` from the UoW
- Repos never know about zvec or events
- `_to_row()` / `_from_row()` serialization is private to each implementation

---

## SQLite Schema

### PRAGMAs

```python
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("PRAGMA busy_timeout = 5000")
conn.execute("PRAGMA synchronous = NORMAL")
conn.execute("PRAGMA cache_size = -8000")       # 8MB
conn.execute("PRAGMA wal_autocheckpoint = 1000")
```

### Tables

Fresh DDL in `001_initial.sql`. Key differences from PostgreSQL:

| PostgreSQL | SQLite |
|------------|--------|
| `BOOLEAN` | `INTEGER` (0/1) |
| `TEXT[]` | JSON text (`'["a","b"]'`) |
| `NUMERIC(12,2)` | `TEXT` (Decimal precision via string) |
| `vector(384)` column | Removed (lives in zvec) |
| `TIMESTAMPTZ` | `TEXT` (ISO format) |
| `UUID` | `TEXT` |
| `SERIAL` | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| `ON CONFLICT DO UPDATE` | `INSERT OR REPLACE` |
| `$1, $2` params | `?, ?` params |

---

## zvec Collections

### Storage Layout

```
/data/
├── sqlite/
│   ├── flux.db
│   ├── flux.db-wal
│   └── flux.db-shm
└── zvec/
    ├── transaction_embeddings/
    └── memory_embeddings/
```

### Schemas

**transaction_embeddings:** fields `user_id` (STRING), `category` (STRING), `type` (STRING), `date` (STRING). Vector: `embedding` (VECTOR_FP32, 384-dim).

**memory_embeddings:** fields `user_id` (STRING), `memory_type` (STRING). Vector: `embedding` (VECTOR_FP32, 384-dim).

### ZvecStore Interface

```python
class ZvecStore:
    def upsert(self, collection, doc_id, vector, metadata): ...
    def delete(self, collection, doc_id): ...
    def search(self, collection, vector, limit, filter=None) -> list[str]: ...
    def optimize(self, collection): ...
```

---

## Docker

### Single Image (Docker Hub)

Multi-stage build:
1. **Stage 1:** Node.js builds web-ui (`npm run build`)
2. **Stage 2:** Python 3.12 + Nginx + Node.js (for claude-agent-sdk CLI)
   - Nginx serves web-ui static files + proxies `/api/` to uvicorn
   - Entrypoint starts nginx + API server + agent bot

### Usage

```bash
docker run -d \
  -p 80:80 \
  -v flux_data:/data \
  -e TELEGRAM_BOT_TOKEN=... \
  -e CLAUDE_AUTH_TOKEN=... \
  yourname/flux-finance
```

- Port 80: Web UI + API (via Nginx)
- `/data` volume: SQLite DB + zvec collections (persistent)

### Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `DATABASE_PATH` | No | `/data/sqlite/flux.db` |
| `ZVEC_PATH` | No | `/data/zvec` |
| `TELEGRAM_BOT_TOKEN` | For bot | — |
| `CLAUDE_AUTH_TOKEN` | For bot | — |
| `CLAUDE_MODEL` | No | `haiku` |
| `VITE_USER_ID` | No | `demo-user` |

### Docker Compose (developers)

```yaml
services:
  flux:
    build: .
    ports:
      - "80:80"
    volumes:
      - flux_data:/data
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - CLAUDE_AUTH_TOKEN=${CLAUDE_AUTH_TOKEN}

volumes:
  flux_data:
```

---

## Testing

### Structure

| Suite | Location | What | Infra |
|-------|----------|------|-------|
| Unit — models | `core/tests/test_models/` | Pydantic validation | None |
| Unit — repos | `core/tests/test_repositories/` | SQLite repos | Temp SQLite file |
| Unit — vector | `core/tests/test_vector/` | ZvecStore | Temp directory |
| Unit — UoW | `core/tests/test_uow/` | Dual-write, rollback, compensation | Temp SQLite + zvec |
| Unit — events | `core/tests/test_events/` | EventBus pub/sub | None |
| Unit — use cases | `core/tests/test_use_cases/` | Business logic with mocked repos | Mocks |
| E2E — API | `api-server/tests/test_e2e/` | Full HTTP flow with seeded data | Temp SQLite + zvec |
| E2E — MCP | `mcp-server/tests/test_e2e/` | Full MCP protocol with seeded data | Temp SQLite + zvec |
| Perf — API | `api-server/tests/test_perf/` | Latency + concurrency benchmarks | Temp SQLite + zvec |
| Perf — MCP | `mcp-server/tests/test_perf/` | Tool latency benchmarks | Temp SQLite + zvec |

### Test Docker

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

Runs unit → E2E → perf in sequence. No external services.

---

## Dev Script

`dev.sh` — single command to start development:

1. Creates `.venv` via `uv`
2. Installs all packages in editable mode
3. Creates `.dev-data/sqlite/` and `.dev-data/zvec/`
4. Runs SQLite migrations
5. Starts API server (uvicorn `--reload`, port 8000)
6. Starts web UI (Vite dev server, port 5173)
7. Optionally starts agent bot (if tokens set)
8. Ctrl+C stops everything

```bash
./dev.sh
# or with bot:
TELEGRAM_BOT_TOKEN=... CLAUDE_AUTH_TOKEN=... ./dev.sh
```

---

## Deliverables

1. This design doc
2. `USECASES.md` — living use case inventory
3. `STATE-MACHINES.md` — updated state machines
4. `README.md` — updated dev/prod instructions
5. Implementation plan (via writing-plans skill)

## Out of Scope

- Pydantic models (unchanged)
- Embedding service (unchanged)
- Web UI code (unchanged)
- MCP tool registration pattern (unchanged)
- Agent bot runner/session logic (unchanged)
- PostgreSQL data migration (fresh start)
