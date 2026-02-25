import asyncio
from pathlib import Path

import asyncpg


async def migrate(database_url: str):
    """Run pending migrations against the database."""
    conn = await asyncpg.connect(database_url)
    try:
        # Check if migrations table exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='schema_migrations')"
        )
        current_version = 0
        if exists:
            current_version = await conn.fetchval(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            )

        migrations_dir = Path(__file__).parent
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            version = int(sql_file.stem.split("_")[0])
            if version > current_version:
                sql = sql_file.read_text()
                await conn.execute(sql)
                print(f"Applied migration {version}: {sql_file.name}")
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    asyncio.run(migrate(sys.argv[1]))
