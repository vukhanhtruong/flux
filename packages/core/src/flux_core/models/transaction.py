from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCreate(BaseModel):
    user_id: str
    date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str
    description: str
    type: TransactionType
    is_recurring: bool = False
    tags: list[str] = Field(default_factory=list)


class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    category: Optional[str] = None
    description: Optional[str] = None
    type: Optional[TransactionType] = None
    tags: Optional[list[str]] = None


class TransactionOut(BaseModel):
    id: UUID
    user_id: str
    date: date
    amount: Decimal
    category: str
    description: str
    type: TransactionType
    is_recurring: bool
    tags: list[str]
    created_at: datetime
