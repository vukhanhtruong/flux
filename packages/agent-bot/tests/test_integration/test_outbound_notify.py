import asyncio
import asyncpg
import pytest

from flux_bot.db.migrate import run_migrations
from flux_core.migrations.migrate import migrate as run_core_migrations
from flux_bot.db.outbound import OutboundRepository


@pytest.fixture
async def pool(pg_url):
    await run_core_migrations(pg_url)
    await run_migrations(pg_url)
    p = await asyncpg.create_pool(pg_url, min_size=1, max_size=3)
    yield p
    await p.close()


async def test_outbound_notify_fires(pg_url, pool):
    """INSERT into bot_outbound_messages triggers pg_notify on 'new_outbound_message'."""
    received = asyncio.Event()
    payloads = []

    def on_notify(conn, pid, channel, payload):
        payloads.append(payload)
        received.set()

    listener_conn = await asyncpg.connect(pg_url)
    await listener_conn.add_listener("new_outbound_message", on_notify)

    try:
        repo = OutboundRepository(pool)
        msg_id = await repo.insert(user_id="tg:123", text="Notify test")
        await asyncio.wait_for(received.wait(), timeout=5.0)
        assert str(msg_id) in payloads
    finally:
        await listener_conn.remove_listener("new_outbound_message", on_notify)
        await listener_conn.close()
