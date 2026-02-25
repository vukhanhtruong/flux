import asyncio
from flux_bot.orchestrator.queue import UserQueue


async def test_enqueue_and_process():
    """Messages are processed by the handler function."""
    processed = []

    async def handler(msg):
        processed.append(msg)

    queue = UserQueue(handler=handler)
    await queue.start()

    await queue.enqueue({"id": 1, "user_id": "tg:123", "text": "hello"})
    await asyncio.sleep(0.1)

    assert len(processed) == 1
    assert processed[0]["id"] == 1
    queue.stop()


async def test_per_user_serialization():
    """Messages for the same user are processed serially."""
    order = []

    async def handler(msg):
        order.append(f"start-{msg['id']}")
        await asyncio.sleep(0.05)
        order.append(f"end-{msg['id']}")

    queue = UserQueue(handler=handler)
    await queue.start()

    await queue.enqueue({"id": 1, "user_id": "tg:123", "text": "first"})
    await queue.enqueue({"id": 2, "user_id": "tg:123", "text": "second"})
    await asyncio.sleep(0.3)

    assert order == ["start-1", "end-1", "start-2", "end-2"]
    queue.stop()


async def test_different_users_parallel():
    """Messages for different users are processed in parallel."""
    active = []
    max_concurrent = 0

    async def handler(msg):
        nonlocal max_concurrent
        active.append(msg["user_id"])
        max_concurrent = max(max_concurrent, len(active))
        await asyncio.sleep(0.05)
        active.remove(msg["user_id"])

    queue = UserQueue(handler=handler)
    await queue.start()

    await queue.enqueue({"id": 1, "user_id": "tg:111", "text": "a"})
    await queue.enqueue({"id": 2, "user_id": "tg:222", "text": "b"})
    await asyncio.sleep(0.2)

    assert max_concurrent == 2
    queue.stop()
