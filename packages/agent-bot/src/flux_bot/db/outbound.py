"""Repository for bot_outbound_messages table."""

import asyncpg


class OutboundRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def insert(
        self,
        user_id: str,
        text: str,
        sender: str | None = None,
    ) -> int:
        """Insert a pending outbound message and return its ID."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO bot_outbound_messages (user_id, text, sender)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                user_id, text, sender,
            )

    async def fetch_pending(self) -> list[dict]:
        """Fetch all pending outbound messages ordered by creation time."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, text, sender, status, created_at
                FROM bot_outbound_messages
                WHERE status = 'pending'
                ORDER BY created_at
                """
            )
            return [dict(r) for r in rows]

    async def mark_sent(self, msg_id: int) -> None:
        """Mark an outbound message as sent."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_outbound_messages
                SET status = 'sent', sent_at = NOW()
                WHERE id = $1
                """,
                msg_id,
            )

    async def mark_failed(self, msg_id: int, error: str) -> None:
        """Mark an outbound message as failed."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE bot_outbound_messages
                SET status = 'failed', sent_at = NOW(), error = $2
                WHERE id = $1
                """,
                msg_id, error,
            )
