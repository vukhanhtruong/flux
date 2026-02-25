from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class MemoryType(str, Enum):
    conversation = "conversation"
    fact = "fact"
    preference = "preference"


class MemoryCreate(BaseModel):
    user_id: str
    memory_type: MemoryType
    content: str


class MemoryOut(BaseModel):
    id: UUID
    user_id: str
    memory_type: MemoryType
    content: str
    created_at: datetime
