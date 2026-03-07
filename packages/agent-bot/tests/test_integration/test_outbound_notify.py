"""Test outbound message delivery with SQLite.

With SQLite, there is no pg_notify trigger. The OutboundWorker polls
or is woken by EventBus/notify(). This test verifies basic insert+fetch.
"""
from flux_bot.db.outbound import OutboundRepository


async def test_outbound_insert_and_fetch(sqlite_db):
    """Insert an outbound message and verify it appears in pending list."""
    repo = OutboundRepository(sqlite_db)
    msg_id = await repo.insert(user_id="tg:123", text="Notify test")
    assert isinstance(msg_id, int)

    pending = await repo.fetch_pending()
    ids = [m["id"] for m in pending]
    assert msg_id in ids

    msg = next(m for m in pending if m["id"] == msg_id)
    assert msg["text"] == "Notify test"
    assert msg["user_id"] == "tg:123"
