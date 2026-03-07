# flux

A headless, MCP-first personal finance AI agent with a modern web UI.

## Architecture

```
Single Container (Docker)
+----------------------------------------------------------+
|                                                          |
|  Nginx (port 80)                                         |
|    |-- / ---------> static web-ui files                  |
|    |-- /api/ -----> proxy to uvicorn :8000                |
|                                                          |
|  uvicorn (port 8000)                                     |
|    |-- FastAPI routes --> Use Cases --> UoW               |
|                                          |               |
|  Agent Bot (optional)                    |               |
|    |-- claude-agent-sdk                  |               |
|    |-- MCP Server (stdio) -----> Use Cases --> UoW       |
|                                          |               |
|                                 +--------+--------+      |
|                                 |                 |      |
|                              SQLite (WAL)    zvec        |
|                              /data/sqlite   /data/zvec   |
+----------------------------------------------------------+
```

### Layered Architecture

```
MCP/API (thin adapter)
    |
Use Case (business logic + orchestration)
    |
Unit of Work (dual-write coordination + event emission)
    |
Repository (Protocol)          EventBus (pub/sub)
    |                              |
SQLite Implementation    ZvecStore      Subscribers
```

### Message Flow

**Inbound (user -> Claude -> response):**

```
1. User sends Telegram message
   |
2. TelegramChannel stores in bot_messages (status='pending')
   |-- EventBus emits MessageCreated
   |
3. Dispatcher routes to per-user queue
   |
4. UserQueue processes one at a time per user
   |-- Loads session_id (conversation continuity)
   |-- Calls ClaudeRunner
   |
5. ClaudeRunner -> claude-agent-sdk (Python) -> MCP tools
   |
6. Saves session_id, marks processed, sends reply via Telegram
```

## Quick Start

### Development (recommended)

```bash
# Install uv: https://docs.astral.sh/uv/
./dev.sh

# With agent bot:
TELEGRAM_BOT_TOKEN=... CLAUDE_AUTH_TOKEN=... ./dev.sh

# Services:
#   API:    http://localhost:8000
#   Docs:   http://localhost:8000/docs
#   Web UI: http://localhost:5173
```

### Docker Production

```bash
# Build and run
docker compose up --build

# With agent bot
TELEGRAM_BOT_TOKEN=... CLAUDE_AUTH_TOKEN=... docker compose up --build

# Detached
docker compose up -d

# Or run directly
docker run -d -p 80:80 -v flux_data:/data \
  -e TELEGRAM_BOT_TOKEN=... \
  -e CLAUDE_AUTH_TOKEN=... \
  yourname/flux-finance
```

### Testing

```bash
# Run all tests (unit + E2E + perf)
./test-all.sh              # without coverage
./test-all.sh --coverage   # with coverage
```

### Manual Setup

```bash
# Core package
cd packages/core
pip install -e ".[dev,vector,embeddings]"
pytest tests/ -v

# API server
cd packages/api-server
pip install -e ".[dev]"
pytest tests/ -v
uvicorn flux_api.app:app --reload

# MCP server
cd packages/mcp-server
pip install -e ".[dev]"
pytest tests/ -v

# Web UI
cd packages/web-ui
npm install && npm run dev
```

## Project Structure

```
packages/
  core/              # Shared business logic, models, repos, use cases
  api-server/        # FastAPI REST API (port 8000)
  mcp-server/        # FastMCP protocol server (stdio)
  agent-bot/         # Telegram agent orchestrator + MCP bridge
  web-ui/            # React 19 + Vite frontend (port 5173)

dev.sh               # Local dev script (uv + hot reload)
Dockerfile           # Single-container production build
nginx.conf           # Nginx config (static + API proxy)
docker-compose.yml   # Production compose
test-all.sh          # Run all tests (isolated temp DB)
```

## Features

- **Web UI**: Modern React interface for managing finances
- **REST API**: FastAPI backend with full OpenAPI documentation
- **MCP Protocol Server**: Thin MCP interface for Claude Desktop / AI clients
- **Agent Bot**: Telegram-based finance assistant via claude-agent-sdk
- **SQLite + zvec**: Embedded storage with semantic vector search
- **Embeddings**: Vector search via fastembed (all-MiniLM-L6-v2, 384-dim)

## Tech Stack

- **Backend**: Python 3.12, FastAPI, FastMCP 3.0, Pydantic v2
- **Storage**: SQLite (WAL mode) + zvec 0.2.1b0 (vector embeddings)
- **Frontend**: React 19, TypeScript, Vite 7, Tailwind CSS v4
- **AI**: fastembed for embeddings, claude-agent-sdk for agent bot
- **Deploy**: Single Docker container (Python + Nginx + Node.js)

## Documentation

- [CLAUDE.md](./CLAUDE.md) -- Development guidelines and architecture
- [STATE-MACHINES.md](./STATE-MACHINES.md) -- State machine diagrams
- [USECASES.md](./USECASES.md) -- Use case inventory

## License

MIT
