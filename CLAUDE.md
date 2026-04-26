# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

flux is a headless, MCP-first personal finance AI agent with a modern web UI. Users interact via:

- **Web UI**: React 19 + TypeScript + Tailwind CSS
- **REST API**: FastAPI backend
- **Telegram Bot**: Orchestrator using Python Agent SDK
- **MCP Protocol**: FastMCP server for Claude Desktop / other MCP clients

## Monorepo Structure

```
packages/
  core/              # Shared business logic, models, repositories, use cases
  api-server/        # FastAPI REST API
  mcp-server/        # FastMCP protocol server
  agent-bot/         # Telegram bot — Orchestrator with Python Agent SDK
  web-ui/            # React 19 + Vite + TypeScript frontend
```

## Architecture

```
Web UI (React) ──HTTP──▶ Nginx ──proxy──▶ FastAPI ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
Claude Desktop ──MCP───▶ FastMCP Server ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
Telegram ──▶ Agent Bot ──▶ DeepAgentRunner ──▶ flux tools ──▶ Use Cases ──▶ UoW ──▶ SQLite + zvec
```

**Layered architecture in packages/core:**

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

## Key Design Decisions

- **All SQL uses parameterized queries** — never string interpolation
- **Financial amounts** are `Decimal` in Python, `TEXT` in SQLite
- **Every table has `user_id`** — multi-user via `tg:12345` format
- **Strict dual-write** — requests fail unless both SQLite and zvec succeed (UoW enforced)
- **WAL mode** — concurrent reads, serialized writes
- **MCP server has no AI dependency** — purely tools/data

## Development Workflow (NON-NEGOTIABLE)

**TDD is mandatory.** For every feature or bugfix:
1. Write the failing test first
2. Run it to confirm it fails
3. Write the minimal implementation
4. Run tests to confirm they pass
5. Commit with a semantic commit message

**Minimum 90% test coverage** — CI will fail below this threshold.

**Living docs must stay in sync** — update in the SAME COMMIT as code changes:

- **[`docs/STATE-MACHINES.md`](docs/STATE-MACHINES.md)** — state transitions, events, workers, error handling, timing
- **[`docs/USECASES.md`](docs/USECASES.md)** — use case inventory, write/vector/event characteristics
- **[`docs/MESSAGE-FLOWS.md`](docs/MESSAGE-FLOWS.md)** — event flows, handlers, cross-module flows

Failing to update these docs = failing to write tests. Work is not complete until docs reflect code.

**Semantic commit messages:**
- `feat:` new feature
- `fix:` bug fix
- `test:` adding or updating tests
- `refactor:` code restructuring
- `chore:` tooling, CI, dependencies
- `docs:` documentation

## Behavioral Principles

**1. Think Before Coding**
Surface assumptions explicitly. If uncertain, ask. Don't proceed with silent assumptions.

**2. Simplicity First**
Implement only what's requested. No speculative features, unnecessary abstractions, or unused error handling. Ask: "Would a senior engineer find this overcomplicated?"

**3. Surgical Changes**
Only touch code directly related to the request. Preserve existing style. Remove only code YOUR changes made obsolete — not pre-existing issues.

**4. Goal-Driven Execution**
Transform tasks into verifiable success criteria. Define what "done" looks like before starting.

## Reference Documentation

- **[State Machines](docs/STATE-MACHINES.md)** — all stateful components with Mermaid diagrams
- **[Use Cases](docs/USECASES.md)** — inventory with write/vector/event characteristics
- **[Message Flows](docs/MESSAGE-FLOWS.md)** — event flows and handler chains

See `.claude/rules/commands.md` for development commands and environment variables.
