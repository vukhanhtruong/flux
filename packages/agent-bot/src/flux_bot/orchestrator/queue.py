"""Per-user async queue — ensures one agent runs per user at a time."""

import asyncio
import structlog
from collections import defaultdict
from typing import Callable, Awaitable

logger = structlog.get_logger(__name__)


class UserQueue:
    def __init__(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._workers: dict[str, asyncio.Task] = {}
        self._running = False

    async def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        for task in self._workers.values():
            task.cancel()

    async def enqueue(self, msg: dict) -> None:
        """Add a message to the appropriate user queue."""
        user_id = msg["user_id"]
        await self._queues[user_id].put(msg)

        # Ensure a worker exists for this user
        if user_id not in self._workers or self._workers[user_id].done():
            self._workers[user_id] = asyncio.create_task(self._worker(user_id))

    async def _worker(self, user_id: str) -> None:
        """Process messages for a single user serially."""
        queue = self._queues[user_id]
        while not queue.empty():
            msg = await queue.get()
            try:
                await self.handler(msg)
            except Exception:
                logger.exception(f"Error processing message {msg.get('id')} for {user_id}")
            finally:
                queue.task_done()
