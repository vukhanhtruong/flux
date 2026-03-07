# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

flux is a headless, MCP-first personal finance AI agent with a modern web UI. Users can interact via:

- **Web UI**: React 19 + TypeScript + Tailwind CSS (packages/web-ui)
- **REST API**: FastAPI backend (packages/api-server)
- **Telegram Bot**: NanoClaw-style orchestrator using Python Agent SDK (packages/agent-bot)
- **MCP Protocol**: FastMCP server for Claude Desktop / other MCP clients (packages/mcp-server)

The `firebase/` directory contains the legacy browser-based React app (localStorage + Gemini AI). It is **not** the active codebase — it serves only as a reference for the domain model and feature set being ported.

## Monorepo Structure

```
packages/
  core/              # Shared business logic, models, repositories, use cases
  api-server/        # FastAPI REST API
  mcp-server/        # FastMCP protocol server
  agent-bot/         # Telegram bot — NanoClaw-style orchestrator with Python Agent SDK
  web-ui/            # React 19 + Vite + TypeScript frontend
```

## Architecture

```
Web UI (React) ──HTTP──▶ Nginx ──proxy──▶ FastAPI ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
Claude Desktop ──MCP───▶ FastMCP Server ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
Telegram ──▶ Agent Bot ──▶ Claude SDK ──▶ MCP Server ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec

EventBus (in-process pub/sub) connects:
  - MessageCreated → Dispatcher (replaces Poller)
  - OutboundCreated → OutboundWorker (replaces LISTEN/NOTIFY)
  - TransactionCreated, MemoryCreated → future extensibility
```

**Agent Bot message flow**:

1. Telegram receives message → stores in `bot_messages` table
2. EventBus emits `MessageCreated` → Dispatcher routes to per-user queue
3. Queue processes one message at a time per user (parallel across users)
4. `ClaudeRunner` uses `claude-agent-sdk` Python to run Claude with MCP tools (finance tools)
5. Response sent back to user via Telegram, session saved for conversation continuity

**Layered architecture in packages/core**:

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

1. **Validation** — models/ (Pydantic v2)
2. **Business Logic** — use_cases/ (Use Case classes with `execute()` method)
3. **Repository Interfaces** — repositories/ (Protocol classes)
4. **Data Access** — sqlite/ (SQLite implementations), vector/ (zvec implementations)
5. **Infrastructure** — sqlite/database.py (sqlite3 + ThreadPoolExecutor, WAL mode), embeddings/service.py (fastembed)
6. **Coordination** — uow/unit_of_work.py (Unit of Work for strict dual-write), events/bus.py (in-process pub/sub)
7. **Storage** — SQLite (WAL mode) for relational data, zvec 0.2.1b0 for vector embeddings (384-dim via all-MiniLM-L6-v2)

**Thin interface layers**:

- **packages/api-server**: FastAPI routes → instantiate Use Case → call `execute()` → return response
- **packages/mcp-server**: FastMCP tool registration → instantiate Use Case → call `execute()` → return dict
- **packages/agent-bot**: NanoClaw-style orchestrator — uses `claude-agent-sdk` Python which connects to MCP server for tools
- **packages/web-ui**: React components consuming REST API

### Core Package Structure

```
packages/core/src/flux_core/
├── models/            # Pydantic v2 — domain models (unchanged)
├── repositories/      # Protocol interfaces (what repos do)
│   └── bot/           # Bot-specific repo interfaces
├── sqlite/            # SQLite implementations (how repos work)
│   ├── database.py    # Database class (sqlite3 + ThreadPoolExecutor, WAL)
│   ├── migrations/    # Fresh SQLite DDL
│   └── bot/           # Bot-specific SQLite repos
├── vector/            # zvec implementations
│   └── store.py       # ZvecStore wrapper (zvec 0.2.1b0)
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
├── uow/               # Unit of Work (dual-write coordinator)
│   └── unit_of_work.py
└── embeddings/        # fastembed service (unchanged)
```

## Tech Stack

### Backend

- **Python 3.12**, FastMCP 3.0, FastAPI 0.115+, sqlite3, zvec==0.2.1b0, Pydantic v2, fastembed
- **Testing**: pytest, pytest-asyncio (asyncio_mode = "auto"), pytest-benchmark
- **Linting**: ruff (line-length = 100)
- **Build**: hatchling

### Frontend

- **React 19**, TypeScript, Vite 7, React Router DOM v7, Tailwind CSS v4
- **Build**: Vite

### Deploy

- Single Docker container (Python + Nginx + Node.js for Claude CLI)
- SQLite (WAL mode) + zvec stored in `/data/` volume
- Agent Bot requires Node.js + Claude Code CLI (for claude-agent-sdk)

## Commands

### Development (recommended)

```bash
./dev.sh                                           # Start all services with hot reload
TELEGRAM_BOT_TOKEN=... CLAUDE_AUTH_TOKEN=... ./dev.sh  # With agent bot
```

### Core Package

```bash
cd packages/core
pip install -e ".[dev]"
pytest tests/ -v
pytest tests/test_repositories/test_transaction_repo.py -v
pytest tests/test_use_cases/test_transactions.py -v
ruff check src/ tests/
```

### API Server

```bash
cd packages/api-server
pip install -e ".[dev]"
pytest tests/ -v
uvicorn flux_api.app:app --reload    # Dev server on port 8000
```

### MCP Server

```bash
cd packages/mcp-server
pip install -e ".[dev]"
pytest tests/ -v
fastmcp dev src/flux_mcp/server.py  # MCP inspector
```

### Web UI

```bash
cd packages/web-ui
npm install
npm run dev       # Dev server on port 5173
npm run build     # Production build
npm run preview   # Preview production build
```

### Agent Bot

```bash
cd packages/agent-bot
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
python -m main               # Run locally (needs DATABASE_PATH, TELEGRAM_BOT_TOKEN)
```

### Docker

```bash
# Production — single container
docker run -d -p 80:80 -v flux_data:/data \
  -e TELEGRAM_BOT_TOKEN=... -e CLAUDE_AUTH_TOKEN=... \
  yourname/flux-finance

# Development — from source
docker compose up

# Run all tests (unit + E2E + perf)
./test-all.sh              # without coverage
./test-all.sh --coverage   # with coverage
```

### Running Migrations

```bash
# Automatic on startup via Database.connect() + migrate()
# Or manually:
python -c "
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
db = Database('/data/sqlite/flux.db')
db.connect()
migrate(db)
"
```

## Development Workflow

**TDD is mandatory.** For every feature or bugfix:

1. Write the failing test first
2. Run it to confirm it fails
3. Write the minimal implementation
4. Run tests to confirm they pass
5. Commit with a semantic commit message

**Minimum 80% test coverage** — CI will fail below this threshold.

**Semantic commit messages** — all commits must follow this format:

- `feat:` new feature
- `fix:` bug fix
- `test:` adding or updating tests
- `refactor:` code restructuring
- `chore:` tooling, CI, dependencies
- `docs:` documentation

## Design Patterns

### Use Case Pattern

Every business operation is a Use Case class with an `execute()` method. See `USECASES.md` for the complete inventory.

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

### Unit of Work Pattern

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

### Repository Pattern

- **Interfaces** in `repositories/` — Protocol classes defining method signatures
- **Implementations** in `sqlite/` — pure SQL, take `sqlite3.Connection` from UoW
- Repos accept and return Pydantic models at the interface boundary
- Repos never know about zvec or events — that's the UoW's job

### Event Bus Pattern

In-process async pub/sub replacing PostgreSQL LISTEN/NOTIFY:

- Subscribers are `async` callables
- One subscriber failure doesn't block others (error logged, continues)
- Events emitted only after successful UoW commit

## Testing

- **Unit tests** (`test_models/`): Pydantic validation, no external deps
- **Repository tests** (`test_repositories/`): SQLite repos against temp SQLite file
- **Vector tests** (`test_vector/`): ZvecStore against temp directory
- **UoW tests** (`test_uow/`): Dual-write, rollback, compensation
- **Event tests** (`test_events/`): EventBus pub/sub
- **Use case tests** (`test_use_cases/`): Business logic with mocked repos
- **E2E tests** (`test_e2e/`): Full protocol via seeded SQLite + zvec
- **Performance tests** (`test_perf/`): Latency + concurrency benchmarks via pytest-benchmark

All async tests use `pytest-asyncio` with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` decorator needed.

## Key Design Decisions

- **All SQL uses parameterized queries** via sqlite3 (`?` placeholders) — never string interpolation
- **Financial amounts** are `Decimal` in Python, stored as `TEXT` in SQLite for precision
- **Every table has `user_id`** — supports multi-user via messaging platform user IDs (e.g., `tg:12345`)
- **Strict dual-write** — requests fail unless both SQLite and zvec writes succeed (enforced by UoW)
- **Embeddings live in zvec, not SQLite** — SQLite stores relational data only, zvec stores vector embeddings
- **Single SQLite database** — core tables + bot tables in one file, `bot_` prefix for namespace separation
- **WAL mode** — concurrent reads, serialized writes, `synchronous=NORMAL` for performance
- **MCP tools are registered via `register_*_tools()` functions** — each tools file exports a registration function called during server setup
- **MCP server has no AI provider dependency** — it's purely tools/data; the agent orchestrator owns AI reasoning
- **Agent Bot uses Claude CLI as subprocess** — spawns `claude -p` with `--mcp-config` for MCP tools, `--resume` for session continuity

## Storage Layout

```
/data/
├── sqlite/
│   ├── flux.db           # SQLite database (WAL mode)
│   ├── flux.db-wal       # Write-ahead log (automatic)
│   └── flux.db-shm       # Shared memory (automatic)
└── zvec/
    ├── transaction_embeddings/   # zvec collection
    └── memory_embeddings/        # zvec collection
```

Environment variables:

- `DATABASE_PATH` — SQLite file path (default: `/data/sqlite/flux.db`)
- `ZVEC_PATH` — zvec data directory (default: `/data/zvec`)

## Reference Documentation

- **[State Machine Diagrams](STATE-MACHINES.md)** — Mermaid diagrams with input/output schema contracts and dataflow for all backend stateful components: EventBus, Unit of Work, Database Connection, message pipeline, outbound delivery, scheduled tasks, subscription/savings lifecycles, and session management. **Keep this file in sync** — update `STATE-MACHINES.md` whenever stateful logic changes.
- **[Use Cases](USECASES.md)** — Living document inventorying all use cases with their write/vector/event characteristics. **Keep this file in sync** — update `USECASES.md` whenever use cases are added, removed, or modified.
