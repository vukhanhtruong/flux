"""SendOutbound use case — mark outbound message as sent or failed."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flux_core.sqlite.bot.outbound_repo import SqliteBotOutboundRepository

if TYPE_CHECKING:
    from flux_core.uow.unit_of_work import UnitOfWork


class SendOutbound:
    """Mark an outbound message as sent or failed (write via UoW)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def mark_sent(self, msg_id: int) -> None:
        async with self._uow:
            repo = SqliteBotOutboundRepository(self._uow.conn)
            repo.mark_sent(msg_id)
            await self._uow.commit()

    async def mark_failed(self, msg_id: int, error: str) -> None:
        async with self._uow:
            repo = SqliteBotOutboundRepository(self._uow.conn)
            repo.mark_failed(msg_id, error)
            await self._uow.commit()
