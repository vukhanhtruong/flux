"""String enums for bot entity statuses."""
from enum import StrEnum


class MessageStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class OutboundStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class TaskStatus(StrEnum):
    active = "active"
    paused = "paused"
    completed = "completed"
