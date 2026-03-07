from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    timestamp: datetime


@dataclass(frozen=True)
class MessageCreated(Event):
    message_id: int
    user_id: str


@dataclass(frozen=True)
class OutboundCreated(Event):
    outbound_id: int
    user_id: str


@dataclass(frozen=True)
class TransactionCreated(Event):
    transaction_id: str
    user_id: str


@dataclass(frozen=True)
class TransactionUpdated(Event):
    transaction_id: str
    user_id: str


@dataclass(frozen=True)
class TransactionDeleted(Event):
    transaction_id: str
    user_id: str


@dataclass(frozen=True)
class MemoryCreated(Event):
    memory_id: str
    user_id: str


@dataclass(frozen=True)
class SubscriptionCreated(Event):
    subscription_id: str
    user_id: str


@dataclass(frozen=True)
class SavingsCreated(Event):
    savings_id: str
    user_id: str


@dataclass(frozen=True)
class ScheduledTaskCreated(Event):
    task_id: int
    user_id: str


@dataclass(frozen=True)
class ScheduledTaskDue(Event):
    task_id: int
    user_id: str
