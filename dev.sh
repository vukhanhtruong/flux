#!/usr/bin/env bash
#
# dev.sh — Start FluxFinance local development with hot reload.
#
# Usage:
#   ./dev.sh                                                    # API + Web UI
#   TELEGRAM_BOT_TOKEN=... CLAUDE_AUTH_TOKEN=... ./dev.sh       # + Agent Bot
#
# Requirements: uv (https://docs.astral.sh/uv/), node >= 20
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Load .env if present (export vars so subprocesses see them)
if [ -f "$ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
fi
VENV="$ROOT/.venv"
DATA="$ROOT/.dev-data"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[dev]${NC} $*"; }
warn()  { echo -e "${YELLOW}[dev]${NC} $*"; }

# --- 1. Python venv via uv ------------------------------------------------
if ! command -v uv &>/dev/null; then
    echo "Error: uv is not installed. Install it: https://docs.astral.sh/uv/"
    exit 1
fi

if [ ! -d "$VENV" ]; then
    info "Creating virtual environment with uv..."
    uv venv "$VENV" --python 3.12
fi

info "Activating venv..."
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# --- 2. Install packages in editable mode ---------------------------------
info "Installing packages in editable mode..."
uv pip install -e "$ROOT/packages/core[dev,vector,embeddings]" \
               -e "$ROOT/packages/api-server[dev]" \
               -e "$ROOT/packages/mcp-server[dev]" \
               -e "$ROOT/packages/agent-bot[dev]" \
               --quiet

# --- 3. Data directories ---------------------------------------------------
mkdir -p "$DATA/sqlite" "$DATA/zvec"
export DATABASE_PATH="$DATA/sqlite/flux.db"
export ZVEC_PATH="$DATA/zvec"
info "Data dir: $DATA"

# --- 4. Run migrations -----------------------------------------------------
info "Running SQLite migrations..."
python -c "
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
db = Database('$DATA/sqlite/flux.db')
db.connect()
migrate(db)
db.disconnect()
print('Migrations complete.')
"

# --- 5. Derive VITE_USER_ID from TELEGRAM_ALLOW_FROM ----------------------
if [ -n "${TELEGRAM_ALLOW_FROM:-}" ]; then
    export VITE_USER_ID="tg:${TELEGRAM_ALLOW_FROM}"
    info "Web UI user: $VITE_USER_ID"
fi

# --- 6. Start services ------------------------------------------------------
PIDS=()

cleanup() {
    info "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    info "All services stopped."
}
trap cleanup EXIT INT TERM

# API server (uvicorn with hot reload)
info "Starting API server on port 8000..."
uvicorn flux_api.app:app \
    --host 0.0.0.0 --port 8000 --reload \
    --reload-dir "$ROOT/packages/core/src" \
    --reload-dir "$ROOT/packages/api-server/src" &
PIDS+=($!)

# Web UI (Vite dev server)
if [ -d "$ROOT/packages/web-ui" ] && command -v npm &>/dev/null; then
    info "Starting Web UI on port 5173..."
    (cd "$ROOT/packages/web-ui" && npm install --silent && npm run dev -- --port 5173) &
    PIDS+=($!)
else
    warn "Skipping Web UI (npm not found or packages/web-ui missing)"
fi

# Agent Bot (optional — only if TELEGRAM_BOT_TOKEN is set)
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    info "Starting Agent Bot (TELEGRAM_BOT_TOKEN is set)..."
    python -m flux_bot.main &
    PIDS+=($!)
else
    warn "Skipping Agent Bot (set TELEGRAM_BOT_TOKEN to enable)"
fi

echo ""
info "=== FluxFinance Dev Server ==="
info "  API:    http://localhost:8000"
info "  Docs:   http://localhost:8000/docs"
info "  Web UI: http://localhost:5173"
info "  Data:   $DATA"
info ""
info "Press Ctrl+C to stop all services."
echo ""

# Wait for all background processes
wait
