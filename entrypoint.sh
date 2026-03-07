#!/usr/bin/env bash
#
# Entrypoint for single-container FluxFinance deployment.
# Starts: Nginx (static + proxy) + API server + Agent Bot (if tokens set)
#
set -euo pipefail

echo "[entrypoint] Starting FluxFinance..."

# Run migrations
echo "[entrypoint] Running SQLite migrations..."
python -c "
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate
db = Database('${DATABASE_PATH:-/data/sqlite/flux.db}')
db.connect()
migrate(db)
db.disconnect()
print('[entrypoint] Migrations complete.')
"

PIDS=()

cleanup() {
    echo "[entrypoint] Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

# Start Nginx (foreground-ready, but we background it here)
echo "[entrypoint] Starting Nginx..."
nginx &
PIDS+=($!)

# Start API server
echo "[entrypoint] Starting API server on port 8000..."
uvicorn flux_api.app:app --host 127.0.0.1 --port 8000 --workers 1 &
PIDS+=($!)

# Start Agent Bot (only if TELEGRAM_BOT_TOKEN is set)
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "[entrypoint] Starting Agent Bot..."
    python -m flux_bot.main &
    PIDS+=($!)
else
    echo "[entrypoint] Agent Bot skipped (TELEGRAM_BOT_TOKEN not set)"
fi

echo "[entrypoint] FluxFinance is running."

# Wait for any process to exit
wait -n
echo "[entrypoint] A process exited, shutting down..."
cleanup
