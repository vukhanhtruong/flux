from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    user_id: str
    name: str
    target_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    deadline: Optional[date] = None
    color: str = "#3B82F6"


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    deadline: Optional[date] = None
    color: Optional[str] = None


class GoalOut(BaseModel):
    id: UUID
    user_id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: Optional[date]
    color: str
