import asyncpg
from flux_bot.db.migrate import run_migrations
from flux_bot.db.onboarding import OnboardingRepository


async def _setup(pg_url: str) -> OnboardingRepository:
    await run_migrations(pg_url)
    pool = await asyncpg.create_pool(pg_url)
    return OnboardingRepository(pool)


async def test_upsert_and_get(pg_url):
    repo = await _setup(pg_url)
    try:
        await repo.upsert(platform_id="111", channel="telegram", step="currency")
        row = await repo.get(platform_id="111", channel="telegram")
        assert row is not None
        assert row["step"] == "currency"
        assert row["currency"] is None
    finally:
        await repo.pool.close()


async def test_upsert_advances_step(pg_url):
    repo = await _setup(pg_url)
    try:
        await repo.upsert("222", "telegram", "currency")
        await repo.upsert("222", "telegram", "timezone", currency="VND")
        row = await repo.get("222", "telegram")
        assert row["step"] == "timezone"
        assert row["currency"] == "VND"
    finally:
        await repo.pool.close()


async def test_delete(pg_url):
    repo = await _setup(pg_url)
    try:
        await repo.upsert("333", "telegram", "currency")
        await repo.delete("333", "telegram")
        row = await repo.get("333", "telegram")
        assert row is None
    finally:
        await repo.pool.close()
