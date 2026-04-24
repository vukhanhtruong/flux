"""flux flush — print and mark-sent pending outbound messages.

Public API
----------
flush(outbound_repo, *, user_id) -> int
    Print all pending outbound messages for the given user_id, mark them sent,
    and return the count of messages flushed.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_bot.db.outbound import OutboundRepository


async def flush(outbound_repo: "OutboundRepository", *, user_id: str) -> int:
    """Print and mark-sent all pending outbound messages for user_id.

    Parameters
    ----------
    outbound_repo:
        Pre-constructed OutboundRepository instance.
    user_id:
        Only messages belonging to this user are processed.

    Returns
    -------
    int
        The count of messages flushed.
    """
    msgs = await outbound_repo.fetch_pending()
    user_msgs = [m for m in msgs if m["user_id"] == user_id]

    if not user_msgs:
        print("No pending messages.")
        return 0

    for msg in user_msgs:
        print(msg["text"])
        await outbound_repo.mark_sent(msg["id"])

    return len(user_msgs)
