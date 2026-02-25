"""Base channel interface."""

from abc import ABC, abstractmethod


class Channel(ABC):
    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel."""

    @abstractmethod
    async def send_message(self, platform_id: str, text: str) -> None:
        """Send a message back to a user. platform_id is the raw platform identifier."""

    async def send_outbound(self, platform_id: str, text: str, sender: str | None = None) -> None:
        """Deliver an outbound message queued by the agent (via OutboundWorker).
        Subclasses must override this to enable agent-initiated messages."""
        raise NotImplementedError(f"{type(self).__name__} does not implement send_outbound")

    async def send_typing_action(self, platform_id: str) -> None:
        """Signal that the bot is typing. No-op by default."""
