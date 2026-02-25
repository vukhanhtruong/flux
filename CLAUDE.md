# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

flux is a headless, MCP-first personal finance AI agent with a modern web UI. Users can interact via:
- **Web UI**: React 19 + TypeScript + Tailwind CSS (packages/web-ui)
- **REST API**: FastAPI backend (packages/api-server)
- **Telegram Bot**: NanoClaw-style orchestrator that spawns Claude Code CLI (packages/agent-bot)
- **MCP Protocol**: FastMCP server for Claude Desktop / other MCP clients (packages/mcp-server)

The `firebase/` directory contains the legacy browser-based React app (localStorage + Gemini AI). It is **not** the active codebase — it serves only as a reference for the domain model and feature set being ported.

## Monorepo Structure

```
packages/
  core/              # Shared business logic, models, DB access
  api-server/        # FastAPI REST API
  mcp-server/        # FastMCP protocol server
  agent-bot/         # Telegram bot — NanoClaw-style orchestrator with Claude CLI
  web-ui/            # React 19 + Vite + TypeScript frontend
```

## Architecture

```
Web UI (React) ──HTTP──▶ FastAPI Server ──▶ Core Package ──▶ PostgreSQL + pgvector
Claude Desktop ──MCP───▶ FastMCP Server ──▶      ↑
                                            ──────┘
Telegram ──▶ Agent Bot (Python orchestrator)
               ├── polls bot_messages table
               ├── per-user async queues
               └── spawns Claude CLI subprocess
                     └── connects to MCP Server (stdio) ──▶ Core Package
```

**Agent Bot message flow**:
1. Telegram receives message → stores in `bot_messages` table
2. Poller polls `bot_messages` every 2s → dispatches to per-user queue
3. Queue processes one message at a time per user (parallel across users)
4. `ClaudeRunner` spawns `claude -p` subprocess with `--mcp-config` (finance tools)
5. Response sent back to user via Telegram, session saved for conversation continuity

**Layered architecture in packages/core**:

1. **Validation** — models/ (Pydantic v2)
2. **Business Logic** — tools/\*.py
3. **Data Access** — db/\*\_repo.py
4. **Infrastructure** — db/connection.py (asyncpg pool), embeddings/service.py (sentence-transformers)
5. **Storage** — PostgreSQL 16 + pgvector (384-dim vectors via all-MiniLM-L6-v2)

**Thin interface layers**:
- **packages/api-server**: FastAPI routes delegating to core tools
- **packages/mcp-server**: FastMCP tool registration delegating to core tools
- **packages/agent-bot**: NanoClaw-style orchestrator — spawns Claude CLI which connects to MCP server for tools
- **packages/web-ui**: React components consuming REST API

## Tech Stack

### Backend
- **Python 3.12**, FastMCP 3.0, FastAPI 0.115+, asyncpg, pgvector, Pydantic v2, sentence-transformers
- **Testing**: pytest, pytest-asyncio (asyncio_mode = "auto"), testcontainers[postgres]
- **Linting**: ruff (line-length = 100)
- **Build**: hatchling

### Frontend
- **React 19**, TypeScript, Vite 7, React Router DOM v7, Tailwind CSS v4
- **Build**: Vite

### Deploy
- Docker Compose (PostgreSQL, Ollama, API server, MCP server, Agent Bot, Web UI)
- Agent Bot container includes Node.js + Claude Code CLI (npm)

## Commands

### Core Package

```bash
cd packages/core
pip install -e ".[dev]"
pytest tests/ -v
pytest tests/test_db/test_connection.py -v
pytest tests/test_db/test_connection.py::test_connect_and_query -v
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
python -m main               # Run locally (needs DATABASE_URL, TELEGRAM_BOT_TOKEN)
```

### Docker Compose

```bash
# From repository root
docker compose up -d postgres         # PostgreSQL only
docker compose up -d api-server       # API + PostgreSQL
docker compose up                     # All services (API, MCP, Web UI, PostgreSQL)
```

### Running Migrations

```bash
cd packages/core
python -m flux_core.migrations.migrate postgresql://localhost/flux
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

## Testing

- **Unit tests** (`test_models/`): Pydantic validation, no external deps
- **Integration tests** (`test_db/`): Repository layer against real PostgreSQL via testcontainers — the `pg_url` fixture in `conftest.py` provides the connection URL from a session-scoped pgvector container
- **Tool tests** (`test_tools/`): MCP tools with mocked repositories
- **E2E tests** (`test_e2e/`): Full MCP protocol via FastMCP `Client` connected to the server

All async tests use `pytest-asyncio` with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` decorator needed.

## Key Design Decisions

- **All SQL uses parameterized queries** via asyncpg (`$1`, `$2`, etc.) — never string interpolation
- **Financial amounts** are `Decimal` in Python, `NUMERIC(12,2)` in PostgreSQL
- **Every table has `user_id`** — supports multi-user via messaging platform user IDs (e.g., `tg:12345`)
- **Embeddings are optional** — transactions store without embeddings if the model isn't loaded; can backfill later
- **MCP tools are registered via `register_*_tools()` functions** — each tools file exports a registration function called during server setup
- **MCP server has no AI provider dependency** — it's purely tools/data; the agent orchestrator owns AI reasoning
- **Agent Bot uses Claude CLI as subprocess** — spawns `claude -p` with `--mcp-config` for MCP tools, `--resume` for session continuity
- **Agent Bot tables prefixed with `bot_`** — `bot_messages`, `bot_sessions`, `bot_scheduled_tasks` to avoid collisions with core tables
