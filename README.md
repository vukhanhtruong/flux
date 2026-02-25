# flux

A headless, MCP-first personal finance AI agent with a modern web UI.

## Quick Start

```bash
# Start all services via Docker Compose
docker compose up

# Start development stack with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

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
  web-ui/            # React 19 + Vite frontend (port 5173)
```

## Features

- **Web UI**: Modern React interface for managing finances
- **REST API**: FastAPI backend with full OpenAPI documentation
- **MCP Protocol**: Integration with messaging platforms via Nanobot
- **PostgreSQL + pgvector**: Persistent storage with semantic search
- **Embeddings**: Transaction search via sentence-transformers

## Tech Stack

- **Backend**: Python 3.12, FastAPI, FastMCP, asyncpg, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4
- **Database**: PostgreSQL 16 + pgvector
- **AI**: sentence-transformers (all-MiniLM-L6-v2)

## Documentation

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines.

## License

MIT
