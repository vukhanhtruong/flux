"""SendMessage use case — queue an outbound message for delivery."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import OutboundCreated
from flux_core.sqlite.bot.outbound_repo import SqliteBotOutboundRepository

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class SendMessage:
    """Queue an outbound message for delivery to the user's channel."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        user_id: str,
        text: str,
        *,
        sender: str | None = None,
    ) -> dict:
        async with self._uow:
            repo = SqliteBotOutboundRepository(self._uow.conn)
            msg_id = repo.insert(user_id, text, sender)
            self._uow.add_event(
                OutboundCreated(
                    timestamp=datetime.now(UTC),
                    outbound_id=msg_id,
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return {"status": "sent", "message_id": msg_id}
