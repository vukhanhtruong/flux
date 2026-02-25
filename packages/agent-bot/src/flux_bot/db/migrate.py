"""Run agent-bot database migrations."""

import asyncpg
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


async def run_migrations(database_url: str) -> None:
    """Execute all SQL migration files in order."""
    conn = await asyncpg.connect(database_url)
    try:
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = sql_file.read_text()
            await conn.execute(sql)
    finally:
        await conn.close()
