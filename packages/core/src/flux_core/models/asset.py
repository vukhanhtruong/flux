from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    income = "income"
    savings = "savings"


class AssetFrequency(str, Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    at_maturity = "at_maturity"


class AssetCreate(BaseModel):
    user_id: str
    name: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    interest_rate: Decimal = Decimal("0")
    frequency: AssetFrequency
    next_date: date
    category: str
    asset_type: AssetType = AssetType.income
    principal_amount: Optional[Decimal] = None
    compound_frequency: Optional[AssetFrequency] = None
    maturity_date: Optional[date] = None
    start_date: Optional[date] = None


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
    asset_type: AssetType = AssetType.income
    principal_amount: Optional[Decimal] = None
    compound_frequency: Optional[AssetFrequency] = None
    maturity_date: Optional[date] = None
    start_date: Optional[date] = None
