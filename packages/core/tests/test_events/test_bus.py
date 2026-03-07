from __future__ import annotations

from datetime import datetime, timezone

from flux_core.events.bus import EventBus
from flux_core.events.events import MessageCreated, OutboundCreated


async def test_subscribe_and_emit():
    bus = EventBus()
    received: list[MessageCreated] = []

    async def handler(event: MessageCreated) -> None:
        received.append(event)

    bus.subscribe(MessageCreated, handler)

    event = MessageCreated(
        timestamp=datetime.now(timezone.utc), message_id=1, user_id="tg:123"
    )
    await bus.emit(event)

    assert len(received) == 1
    assert received[0] is event
    assert received[0].message_id == 1
    assert received[0].user_id == "tg:123"


async def test_emit_no_subscribers():
    bus = EventBus()
    event = MessageCreated(
        timestamp=datetime.now(timezone.utc), message_id=1, user_id="tg:123"
    )
    # Should not raise
    await bus.emit(event)


async def test_subscriber_error_does_not_block_others():
    bus = EventBus()
    received: list[MessageCreated] = []

    async def bad_handler(event: MessageCreated) -> None:
        raise RuntimeError("boom")

    async def good_handler(event: MessageCreated) -> None:
        received.append(event)

    bus.subscribe(MessageCreated, bad_handler)
    bus.subscribe(MessageCreated, good_handler)

    event = MessageCreated(
        timestamp=datetime.now(timezone.utc), message_id=1, user_id="tg:123"
    )
    await bus.emit(event)

    assert len(received) == 1
    assert received[0] is event


async def test_unsubscribe():
    bus = EventBus()
    received: list[MessageCreated] = []

    async def handler(event: MessageCreated) -> None:
        received.append(event)

    bus.subscribe(MessageCreated, handler)
    bus.unsubscribe(MessageCreated, handler)

    event = MessageCreated(
        timestamp=datetime.now(timezone.utc), message_id=1, user_id="tg:123"
    )
    await bus.emit(event)

    assert len(received) == 0


async def test_multiple_event_types():
    bus = EventBus()
    messages: list[MessageCreated] = []
    outbounds: list[OutboundCreated] = []

    async def msg_handler(event: MessageCreated) -> None:
        messages.append(event)

    async def out_handler(event: OutboundCreated) -> None:
        outbounds.append(event)

    bus.subscribe(MessageCreated, msg_handler)
    bus.subscribe(OutboundCreated, out_handler)

    msg_event = MessageCreated(
        timestamp=datetime.now(timezone.utc), message_id=1, user_id="tg:123"
    )
    out_event = OutboundCreated(
        timestamp=datetime.now(timezone.utc), outbound_id=2, user_id="tg:456"
    )

    await bus.emit(msg_event)
    await bus.emit(out_event)

    assert len(messages) == 1
    assert messages[0] is msg_event
    assert len(outbounds) == 1
    assert outbounds[0] is out_event
