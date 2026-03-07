"""Bot repository Protocol interfaces."""

from flux_core.repositories.bot.message_repo import BotMessageRepository
from flux_core.repositories.bot.outbound_repo import BotOutboundRepository
from flux_core.repositories.bot.scheduled_task_repo import BotScheduledTaskRepository
from flux_core.repositories.bot.session_repo import BotSessionRepository

__all__ = [
    "BotMessageRepository",
    "BotOutboundRepository",
    "BotScheduledTaskRepository",
    "BotSessionRepository",
]
