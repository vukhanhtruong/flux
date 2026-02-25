from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class BillingCycle(str, Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionCreate(BaseModel):
    user_id: str
    name: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    billing_cycle: BillingCycle
    next_date: date
    category: str


class SubscriptionOut(BaseModel):
    id: UUID
    user_id: str
    name: str
    amount: Decimal
    billing_cycle: BillingCycle
    next_date: date
    category: str
    active: bool
