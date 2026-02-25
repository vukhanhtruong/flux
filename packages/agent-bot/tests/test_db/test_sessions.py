import asyncpg
from flux_bot.db.migrate import run_migrations
from flux_bot.db.sessions import SessionRepository


async def _setup(pg_url: str) -> SessionRepository:
    await run_migrations(pg_url)
    pool = await asyncpg.create_pool(pg_url)
    return SessionRepository(pool)


async def test_get_session_returns_none_for_new_user(pg_url):
    repo = await _setup(pg_url)
    try:
        session_id = await repo.get_session_id("tg:new_user")
        assert session_id is None
    finally:
        await repo.pool.close()


async def test_upsert_and_get_session(pg_url):
    repo = await _setup(pg_url)
    try:
        await repo.upsert("tg:123", "session-abc-123")
        session_id = await repo.get_session_id("tg:123")
        assert session_id == "session-abc-123"
    finally:
        await repo.pool.close()


async def test_upsert_overwrites_existing(pg_url):
    repo = await _setup(pg_url)
    try:
        await repo.upsert("tg:123", "old-session")
        await repo.upsert("tg:123", "new-session")
        session_id = await repo.get_session_id("tg:123")
        assert session_id == "new-session"
    finally:
        await repo.pool.close()


async def test_delete_removes_session(pg_url):
    repo = await _setup(pg_url)
    try:
        await repo.upsert("tg:456", "session-to-delete")
        await repo.delete("tg:456")
        session_id = await repo.get_session_id("tg:456")
        assert session_id is None
    finally:
        await repo.pool.close()


async def test_delete_nonexistent_user_is_noop(pg_url):
    repo = await _setup(pg_url)
    try:
        # Should not raise even if the user has no session
        await repo.delete("tg:no-such-user")
    finally:
        await repo.pool.close()
