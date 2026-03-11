#!/usr/bin/env bash
#
# Entrypoint for single-container FluxFinance deployment.
# Starts: Nginx (static + proxy) + API server + Agent Bot (if tokens set)
#
set -euo pipefail

echo "[entrypoint] Starting FluxFinance..."

# Run migrations (as root — before switching user)
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

# Ensure flux user owns data directory (migrations may have created files as root)
chown -R flux:flux /data

# Prepare flux user's home for Claude CLI (needs ~/.claude/ writable)
mkdir -p /home/flux/.claude
chown -R flux:flux /home/flux

# Export HOME for all child processes spawned via gosu
export HOME=/home/flux

PIDS=()

cleanup() {
    echo "[entrypoint] Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

# Start Nginx (as root — needs port 80)
echo "[entrypoint] Starting Nginx..."
nginx &
PIDS+=($!)

# Start API server (as non-root via gosu — cleanly drops privileges)
echo "[entrypoint] Starting API server on port 8000..."
gosu flux uvicorn flux_api.app:app --host 127.0.0.1 --port 8000 --workers 1 &
PIDS+=($!)

# Start Agent Bot (only if TELEGRAM_BOT_TOKEN is set)
# Must run as non-root — Claude CLI refuses --dangerously-skip-permissions as root
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "[entrypoint] Starting Agent Bot (user=$(gosu flux whoami), HOME=$HOME)..."
    gosu flux python -m flux_bot.main &
    PIDS+=($!)
else
    echo "[entrypoint] Agent Bot skipped (TELEGRAM_BOT_TOKEN not set)"
fi

echo "[entrypoint] FluxFinance is running."

# Wait for any process to exit
wait -n
echo "[entrypoint] A process exited, shutting down..."
cleanup
