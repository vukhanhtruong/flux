"""ProcessMessage use case — mark message processed, insert outbound, upsert session."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from flux_core.events.events import OutboundCreated
from flux_core.sqlite.bot.message_repo import SqliteBotMessageRepository
from flux_core.sqlite.bot.outbound_repo import SqliteBotOutboundRepository
from flux_core.sqlite.bot.session_repo import SqliteBotSessionRepository

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class ProcessMessage:
    """Mark a message as processed, store the response, and update the session."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(
        self,
        msg_id: int,
        user_id: str,
        response_text: str,
        session_id: str,
        *,
        sender: str | None = None,
    ) -> dict:
        async with self._uow:
            msg_repo = SqliteBotMessageRepository(self._uow.conn)
            out_repo = SqliteBotOutboundRepository(self._uow.conn)
            session_repo = SqliteBotSessionRepository(self._uow.conn)

            msg_repo.mark_processed(msg_id)
            outbound_id = out_repo.insert(user_id, response_text, sender)
            session_repo.upsert(user_id, session_id)

            self._uow.add_event(
                OutboundCreated(
                    timestamp=datetime.now(UTC),
                    outbound_id=outbound_id,
                    user_id=user_id,
                )
            )
            await self._uow.commit()

        return {
            "msg_id": msg_id,
            "outbound_id": outbound_id,
            "session_id": session_id,
        }
