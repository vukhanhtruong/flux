# flux

A headless, MCP-first personal finance AI agent with a modern web UI.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Docker Compose                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────┐     ┌──────────────────────────────────┐ │
│  │  Telegram   │────▶│  Agent-Bot (Python)              │ │
│  │  (channel)  │◀────│                                   │ │
│  └────────────┘     │  ┌──────────────────────────────┐ │ │
│                      │  │ Orchestrator                   │ │ │
│                      │  │  - Poller (LISTEN/NOTIFY)      │ │ │
│                      │  │  - per-user async queues       │ │ │
│                      │  │  - OutboundWorker (LISTEN/     │ │ │
│                      │  │    NOTIFY, proactive delivery) │ │ │
│                      │  └──────────────┬────────────────┘ │ │
│                      │                 │ spawns            │ │
│                      │                 ▼                   │ │
│                      │  ┌──────────────────────────────┐  │ │
│                      │  │ Node SDK sidecar               │  │ │
│                      │  │  (@anthropic-ai/claude-code)   │  │ │
│                      │  │  - session resume              │  │ │
│                      │  │  - vision (photos)             │  │ │
│                      │  └──────────────┬─────────────────┘  │ │
│                      │                 │ MCP (stdio)         │ │
│                      │                 ▼                     │ │
│                      │  ┌──────────────────────────────┐    │ │
│                      │  │ MCP Server (finance tools)    │    │ │
│                      │  └──────────────────────────────┘    │ │
│                      └──────────────────┬────────────────────┘ │
│                                         │                      │
│                      ┌──────────────────▼─────────────────┐   │
│                      │       PostgreSQL + pgvector          │   │
│                      └────────────────────────────────────┘   │
│                                                               │
│  ┌──────────┐   ┌──────────┐                                  │
│  │  Web UI  │──▶│API Server│──▶ PostgreSQL                    │
│  └──────────┘   └──────────┘                                  │
└──────────────────────────────────────────────────────────────┘
```

### Message Flow

**Inbound (user → Claude → response):**

```
1. User sends Telegram message (text or photo)
   │
   ▼
2. TelegramChannel stores message in bot_messages (status='pending')
   └── PostgreSQL trigger fires pg_notify → 'new_bot_message'
   │
   ▼
3. Poller wakes instantly via LISTEN/NOTIFY (fallback: 30s poll)
   ├── Fetches pending rows, marks each 'processing'
   └── Dispatches to per-user UserQueue
   │
   ▼
4. UserQueue processes one message at a time per user
   ├── Loads session_id from bot_sessions (conversation continuity)
   └── Calls ClaudeRunner
   │
   ▼
5. ClaudeRunner spawns Node.js SDK sidecar
   ├── Sends JSON payload (prompt, session_id, model, MCP config)
   ├── SDK sidecar calls Claude API via @anthropic-ai/claude-code
   └── Returns (response_text, new_session_id)
   │
   ▼
6. Saves new session_id, marks message 'processed', sends reply via Telegram
```

**Outbound (proactive, tool-initiated):**

```
MCP tool writes row to bot_outbound_messages
   └── PostgreSQL trigger fires pg_notify → 'new_outbound_message'
   │
   ▼
OutboundWorker wakes via LISTEN/NOTIFY (fallback: 30s poll)
   ├── Routes message by user_id prefix (tg:, wa:)
   └── Delivers via appropriate channel → marks sent
```

For browser-based flows, `web-ui` calls `api-server` directly, which delegates to the same `core` package and PostgreSQL.

## Quick Start

```bash
# Start all services via Docker Compose
docker compose up

# Start development stack with hot reload
docker compose -f docker-compose.dev.yml up --build

# Or run locally:

# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Run API server (Terminal 1)
cd packages/api-server
pip install -e ".[dev]"
uvicorn flux_api.app:app --reload

# 3. Run Web UI (Terminal 2)
cd packages/web-ui
npm install
npm run dev

# Web UI: http://localhost:5173
# API docs: http://localhost:8000/docs
```

## Project Structure

```
packages/
  core/              # Shared business logic, models, DB access
  api-server/        # FastAPI REST API (port 8000)
  mcp-server/        # FastMCP protocol server (stdio)
  agent-bot/         # Telegram agent orchestrator + MCP bridge
  web-ui/            # React 19 + Vite frontend (port 5173)
```

## Features

- **Web UI**: Modern React interface for managing finances
- **REST API**: FastAPI backend with full OpenAPI documentation
- **MCP Protocol Server**: Thin MCP interface over shared core tools
- **Agent Bot**: Telegram-based finance assistant and tool orchestration layer
- **PostgreSQL + pgvector**: Persistent storage with semantic search
- **Embeddings**: Optional vector search support via FastEmbed

## Tech Stack

- **Backend**: Python 3.12, FastAPI, FastMCP, python-telegram-bot, asyncpg, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4
- **Database**: PostgreSQL 16 + pgvector
- **AI/Embeddings**: FastEmbed (optional, in `core[embeddings]`)

## Documentation

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines.

## License

MIT
