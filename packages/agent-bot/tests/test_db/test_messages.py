import asyncpg
from flux_bot.db.migrate import run_migrations
from flux_bot.db.messages import MessageRepository


async def _setup(pg_url: str) -> MessageRepository:
    await run_migrations(pg_url)
    pool = await asyncpg.create_pool(pg_url)
    return MessageRepository(pool)


async def test_insert_and_fetch_pending(pg_url):
    repo = await _setup(pg_url)
    try:
        msg_id = await repo.insert(
            user_id="tg:truong-vu", channel="telegram", platform_id="123", text="spent 50k lunch"
        )
        assert isinstance(msg_id, int)

        pending = await repo.fetch_pending()
        assert len(pending) >= 1
        msg = next(m for m in pending if m["id"] == msg_id)
        assert msg["platform_id"] == "123"
    finally:
        await repo.pool.close()


async def test_insert_with_image(pg_url):
    repo = await _setup(pg_url)
    try:
        msg_id = await repo.insert(
            user_id="tg:another-user", channel="telegram", platform_id="456",
            text="receipt", image_path="/tmp/receipt.jpg"
        )
        pending = await repo.fetch_pending()
        msg = next(m for m in pending if m["id"] == msg_id)
        assert msg["image_path"] == "/tmp/receipt.jpg"
        assert msg["platform_id"] == "456"
    finally:
        await repo.pool.close()


async def test_mark_processed(pg_url):
    repo = await _setup(pg_url)
    try:
        msg_id = await repo.insert(user_id="tg:truong-vu", channel="telegram", platform_id="123", text="hello")
        await repo.mark_processed(msg_id)

        pending = await repo.fetch_pending()
        assert not any(m["id"] == msg_id for m in pending)
    finally:
        await repo.pool.close()


async def test_mark_failed(pg_url):
    repo = await _setup(pg_url)
    try:
        msg_id = await repo.insert(user_id="tg:truong-vu", channel="telegram", platform_id="123", text="hello")
        await repo.mark_failed(msg_id, "timeout")

        pending = await repo.fetch_pending()
        assert not any(m["id"] == msg_id for m in pending)
    finally:
        await repo.pool.close()
