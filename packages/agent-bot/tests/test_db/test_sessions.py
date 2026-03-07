"""Test SessionRepository — async wrapper around SQLite bot session repo."""
from flux_bot.db.sessions import SessionRepository


async def test_get_session_returns_none_for_new_user(sqlite_db):
    repo = SessionRepository(sqlite_db)
    session_id = await repo.get_session_id("tg:new_user")
    assert session_id is None


async def test_upsert_and_get_session(sqlite_db):
    repo = SessionRepository(sqlite_db)
    await repo.upsert("tg:123", "session-abc-123")
    session_id = await repo.get_session_id("tg:123")
    assert session_id == "session-abc-123"


async def test_upsert_overwrites_existing(sqlite_db):
    repo = SessionRepository(sqlite_db)
    await repo.upsert("tg:123", "old-session")
    await repo.upsert("tg:123", "new-session")
    session_id = await repo.get_session_id("tg:123")
    assert session_id == "new-session"


async def test_delete_removes_session(sqlite_db):
    repo = SessionRepository(sqlite_db)
    await repo.upsert("tg:456", "session-to-delete")
    await repo.delete("tg:456")
    session_id = await repo.get_session_id("tg:456")
    assert session_id is None


async def test_delete_nonexistent_user_is_noop(sqlite_db):
    repo = SessionRepository(sqlite_db)
    await repo.delete("tg:no-such-user")  # Should not raise
