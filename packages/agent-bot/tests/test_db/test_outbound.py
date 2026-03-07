"""Test OutboundRepository — async wrapper around SQLite bot outbound repo."""
from flux_bot.db.outbound import OutboundRepository


async def test_insert_and_fetch_pending(sqlite_db):
    repo = OutboundRepository(sqlite_db)
    msg_id = await repo.insert(user_id="tg:123", text="Hello!", sender="Bot")
    assert isinstance(msg_id, int)

    pending = await repo.fetch_pending()
    assert len(pending) >= 1
    msg = next(m for m in pending if m["id"] == msg_id)
    assert msg["user_id"] == "tg:123"
    assert msg["text"] == "Hello!"
    assert msg["sender"] == "Bot"
    assert msg["status"] == "pending"


async def test_mark_sent(sqlite_db):
    repo = OutboundRepository(sqlite_db)
    msg_id = await repo.insert(user_id="tg:456", text="Update")
    await repo.mark_sent(msg_id)

    pending = await repo.fetch_pending()
    ids = [m["id"] for m in pending]
    assert msg_id not in ids


async def test_mark_failed(sqlite_db):
    repo = OutboundRepository(sqlite_db)
    msg_id = await repo.insert(user_id="tg:789", text="Oops")
    await repo.mark_failed(msg_id, "Connection timeout")

    pending = await repo.fetch_pending()
    ids = [m["id"] for m in pending]
    assert msg_id not in ids

    # Error is stored
    conn = sqlite_db.connection()
    row = conn.execute(
        "SELECT status, error FROM bot_outbound_messages WHERE id = ?", (msg_id,)
    ).fetchone()
    assert row["status"] == "failed"
    assert row["error"] == "Connection timeout"
