"""Test MessageRepository — async wrapper around SQLite bot message repo."""
from flux_bot.db.messages import MessageRepository


async def test_insert_and_fetch_pending(sqlite_db):
    repo = MessageRepository(sqlite_db)
    msg_id = await repo.insert(
        user_id="tg:truong-vu", channel="telegram", platform_id="123", text="spent 50k lunch"
    )
    assert isinstance(msg_id, int)

    pending = await repo.fetch_pending()
    assert len(pending) >= 1
    msg = next(m for m in pending if m["id"] == msg_id)
    assert msg["platform_id"] == "123"


async def test_insert_with_image(sqlite_db):
    repo = MessageRepository(sqlite_db)
    msg_id = await repo.insert(
        user_id="tg:another-user", channel="telegram", platform_id="456",
        text="receipt", image_path="/tmp/receipt.jpg"
    )
    pending = await repo.fetch_pending()
    msg = next(m for m in pending if m["id"] == msg_id)
    assert msg["image_path"] == "/tmp/receipt.jpg"
    assert msg["platform_id"] == "456"


async def test_mark_processed(sqlite_db):
    repo = MessageRepository(sqlite_db)
    msg_id = await repo.insert(
        user_id="tg:truong-vu", channel="telegram", platform_id="123", text="hello"
    )
    await repo.mark_processed(msg_id)

    pending = await repo.fetch_pending()
    assert not any(m["id"] == msg_id for m in pending)


async def test_mark_failed(sqlite_db):
    repo = MessageRepository(sqlite_db)
    msg_id = await repo.insert(
        user_id="tg:truong-vu", channel="telegram", platform_id="123", text="hello"
    )
    await repo.mark_failed(msg_id, "timeout")

    pending = await repo.fetch_pending()
    assert not any(m["id"] == msg_id for m in pending)
