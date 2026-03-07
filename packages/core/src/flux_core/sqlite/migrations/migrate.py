from __future__ import annotations

import structlog
from pathlib import Path

from flux_core.sqlite.database import Database

logger = structlog.get_logger(__name__)
MIGRATIONS_DIR = Path(__file__).parent


def migrate(db: Database) -> None:
    conn = db.connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    conn.commit()

    row = conn.execute("SELECT MAX(version) as v FROM schema_migrations").fetchone()
    current_version = row["v"] if row["v"] is not None else 0

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for sql_file in sql_files:
        version = int(sql_file.name.split("_")[0])
        if version <= current_version:
            continue
        logger.info("Applying migration %s", sql_file.name)
        sql = sql_file.read_text()
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        conn.commit()
        logger.info("Applied migration %s (version %d)", sql_file.name, version)
