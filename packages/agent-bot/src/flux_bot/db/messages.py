"""Repository for bot_messages table."""

import asyncpg


class MessageRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def insert(
        self,
        user_id: str,
        channel: str,
        platform_id: str,
        text: str | None = None,
        image_path: str | None = None,
    ) -> int:
        """Insert a new pending message and return its ID."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO bot_messages (user_id, channel, platform_id, text, image_path)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                user_id, channel, platform_id, text, image_path,
            )

    async def fetch_pending(self) -> list[dict]:
        """Fetch all pending messages ordered by creation time."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, channel, platform_id, text, image_path, created_at
                FROM bot_messages
                WHERE status = 'pending'
                ORDER BY created_at
                """
            )
            return [dict(r) for r in rows]

    async def mark_processing(self, msg_id: int) -> None:
        """Mark a message as being processed."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE bot_messages SET status = 'processing' WHERE id = $1",
                msg_id,
            )

    async def mark_processed(self, msg_id: int) -> None:
        """Mark a message as successfully processed."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_messages SET status = 'processed', processed_at = NOW()
                WHERE id = $1
                """,
                msg_id,
            )

    async def mark_failed(self, msg_id: int, error: str) -> None:
        """Mark a message as failed with an error."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_messages SET status = 'failed', error = $2, processed_at = NOW()
                WHERE id = $1
                """,
                msg_id, error,
            )
