# Development Commands

## Quick Start

```bash
./dev.sh                    # All services with hot reload
TELEGRAM_BOT_TOKEN=... ./dev.sh   # With agent bot
./test-all.sh --coverage    # Full test suite
```

## Core Package

```bash
cd packages/core
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
```

## API Server

```bash
cd packages/api-server
pip install -e ".[dev]"
pytest tests/ -v
uvicorn flux_api.app:app --reload    # Port 8000
```

## MCP Server

```bash
cd packages/mcp-server
pip install -e ".[dev]"
pytest tests/ -v
fastmcp dev src/flux_mcp/server.py   # MCP inspector
```

## Web UI

```bash
cd packages/web-ui
npm install
npm run dev       # Port 5173
npm run build     # Production build
npm run preview   # Preview production
```

## Agent Bot

```bash
cd packages/agent-bot
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
python -m main    # Needs DATABASE_PATH, TELEGRAM_BOT_TOKEN
```

## Docker

```bash
# Production
docker run -d -p 80:80 -v flux_data:/data \
  -e TELEGRAM_BOT_TOKEN=... \
  yourname/flux-finance

# Development
docker compose up
```

## Migrations

```bash
# Automatic on startup via Database.connect() + migrate()
# Manual:
python -c "
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
db = Database('/data/sqlite/flux.db')
db.connect()
migrate(db)
"
```

## Storage Layout

```
/data/
├── backups/                      # Backup archives (.zip)
├── sqlite/
│   ├── flux.db                   # SQLite database (WAL mode)
│   ├── flux.db-wal               # Write-ahead log
│   └── flux.db-shm               # Shared memory
└── zvec/
    ├── transaction_embeddings/   # zvec collection
    └── memory_embeddings/        # zvec collection
```

## Environment Variables

- `DATABASE_PATH` — SQLite file path (default: `/data/sqlite/flux.db`)
- `ZVEC_PATH` — zvec data directory (default: `/data/zvec`)
- `FLUX_SECRET_KEY` — Encryption key for sensitive config
- `BACKUP_LOCAL_DIR` — Local backup directory (default: `/data/backups`)
- `BACKUP_LOCAL_RETENTION` — Max local backups (default: `7`)
- `BACKUP_S3_RETENTION` — Max S3 backups (default: `30`)
