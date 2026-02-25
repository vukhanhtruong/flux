"""Repository for bot_onboarding table."""

import asyncpg


class OnboardingRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get(self, platform_id: str, channel: str) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT platform_id, channel, step, currency, timezone
                FROM bot_onboarding WHERE platform_id = $1 AND channel = $2
                """,
                platform_id, channel,
            )
            return dict(row) if row else None

    async def upsert(
        self,
        platform_id: str,
        channel: str,
        step: str,
        currency: str | None = None,
        timezone: str | None = None,
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_onboarding (platform_id, channel, step, currency, timezone)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (platform_id, channel) DO UPDATE
                    SET step = $3,
                        currency = COALESCE($4, bot_onboarding.currency),
                        timezone = COALESCE($5, bot_onboarding.timezone)
                """,
                platform_id, channel, step, currency, timezone,
            )

    async def delete(self, platform_id: str, channel: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bot_onboarding WHERE platform_id = $1 AND channel = $2",
                platform_id, channel,
            )
