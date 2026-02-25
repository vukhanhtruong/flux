import asyncpg
import pytest

from flux_bot.db.outbound import OutboundRepository
from flux_bot.db.migrate import run_migrations
from flux_core.migrations.migrate import migrate as run_core_migrations


@pytest.fixture
async def pool(pg_url):
    await run_core_migrations(pg_url)
    await run_migrations(pg_url)
    p = await asyncpg.create_pool(pg_url, min_size=1, max_size=3)
    yield p
    await p.close()


@pytest.fixture
def repo(pool):
    return OutboundRepository(pool)


async def test_insert_and_fetch_pending(repo):
    msg_id = await repo.insert(user_id="tg:123", text="Hello!", sender="Bot")
    assert isinstance(msg_id, int)

    pending = await repo.fetch_pending()
    assert len(pending) >= 1
    msg = next(m for m in pending if m["id"] == msg_id)
    assert msg["user_id"] == "tg:123"
    assert msg["text"] == "Hello!"
    assert msg["sender"] == "Bot"
    assert msg["status"] == "pending"


async def test_mark_sent(repo):
    msg_id = await repo.insert(user_id="tg:456", text="Update")
    await repo.mark_sent(msg_id)

    pending = await repo.fetch_pending()
    ids = [m["id"] for m in pending]
    assert msg_id not in ids


async def test_mark_failed(repo):
    msg_id = await repo.insert(user_id="tg:789", text="Oops")
    await repo.mark_failed(msg_id, "Connection timeout")

    pending = await repo.fetch_pending()
    ids = [m["id"] for m in pending]
    assert msg_id not in ids
