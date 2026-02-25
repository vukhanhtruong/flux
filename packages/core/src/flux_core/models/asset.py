from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class AssetFrequency(str, Enum):
    monthly = "monthly"
    yearly = "yearly"


class AssetCreate(BaseModel):
    user_id: str
    name: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    interest_rate: Decimal = Decimal("0")
    frequency: AssetFrequency
    next_date: date
    category: str


class AssetOut(BaseModel):
    id: UUID
    user_id: str
    name: str
    amount: Decimal
    interest_rate: Decimal
    frequency: AssetFrequency
    next_date: date
    category: str
    active: bool
