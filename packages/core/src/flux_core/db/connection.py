import asyncpg


class Database:
    """Async PostgreSQL connection pool manager."""

    def __init__(self, url: str):
        self._url = url
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            self._url,
            min_size=2,
            max_size=10,
            max_inactive_connection_lifetime=300,
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
