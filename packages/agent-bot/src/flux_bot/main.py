"""flux Agent Bot — NanoClaw-style orchestrator."""

import asyncio
import logging
import signal

import asyncpg

from flux_bot.config import load_config
from flux_bot.db.migrate import run_migrations
from flux_core.migrations.migrate import migrate as run_core_migrations
from flux_bot.db.messages import MessageRepository
from flux_bot.db.sessions import SessionRepository
from flux_bot.channels.telegram import TelegramChannel
from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.db.outbound import OutboundRepository
from flux_bot.orchestrator.outbound import OutboundWorker
from flux_bot.db.scheduled_tasks import ScheduledTaskRepository
from flux_bot.orchestrator.scheduler import SchedulerWorker
from flux_bot.orchestrator.poller import Poller
from flux_bot.orchestrator.queue import UserQueue
from flux_bot.runner.sdk import ClaudeRunner
from flux_core.db.connection import Database
from flux_core.db.user_profile_repo import UserProfileRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    config = load_config()
    logger.info("Starting flux Agent Bot (orchestrator mode)...")

    await run_core_migrations(config.database_url)
    await run_migrations(config.database_url)
    logger.info("Migrations complete")

    pool = await asyncpg.create_pool(config.database_url, min_size=2, max_size=10)
    logger.info("Database connected")

    core_db = Database(config.database_url)
    await core_db.connect()

    msg_repo = MessageRepository(pool)
    session_repo = SessionRepository(pool)
    task_repo = ScheduledTaskRepository(pool)
    profile_repo = UserProfileRepository(core_db)

    runner = ClaudeRunner(
        mcp_config_path=config.runner.mcp_config_path,
        timeout=config.runner.timeout,
        model=config.runner.model,
        max_turns=config.runner.max_turns,
        system_prompt=config.runner.system_prompt_path,
    )

    channels: dict[str, object] = {}

    if config.telegram.enabled and config.telegram.bot_token:
        telegram = TelegramChannel(
            bot_token=config.telegram.bot_token,
            message_repo=msg_repo,
            profile_repo=profile_repo,
            session_repo=session_repo,
            task_repo=task_repo,
            allow_from=config.telegram.allow_from or None,
            image_dir=config.image_dir,
        )
        await telegram.start()
        channels["telegram"] = telegram
        logger.info("Telegram channel started")

    if not channels:
        logger.warning("No channels enabled! Set TELEGRAM_BOT_TOKEN.")

    handle_message = make_handle_message(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        channels=channels,
    )

    queue = UserQueue(handler=handle_message)
    await queue.start()
    poller = Poller(
        message_repo=msg_repo,
        queue=queue,
        poll_interval=config.poll_interval,
        database_url=config.database_url,
        fallback_poll_interval=config.fallback_poll_interval,
    )

    outbound_repo = OutboundRepository(pool)
    outbound_worker = OutboundWorker(
        outbound_repo=outbound_repo,
        channels=channels,
        poll_interval=config.poll_interval,
        database_url=config.database_url,
        fallback_poll_interval=config.fallback_poll_interval,
    )

    scheduler_worker = SchedulerWorker(
        task_repo=task_repo,
        message_repo=msg_repo,
        poll_interval=config.fallback_poll_interval,
    )

    poller_task = asyncio.create_task(poller.start())
    outbound_task = asyncio.create_task(outbound_worker.start())
    scheduler_task = asyncio.create_task(scheduler_worker.start())
    logger.info("Orchestrator running. Press Ctrl+C to stop.")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()

    logger.info("Shutting down...")
    poller.stop()
    queue.stop()
    outbound_worker.stop()
    scheduler_worker.stop()
    poller_task.cancel()
    outbound_task.cancel()
    scheduler_task.cancel()
    await poller.close()
    await outbound_worker.close()
    for ch in channels.values():
        await ch.stop()
    await core_db.disconnect()
    await pool.close()
    logger.info("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
