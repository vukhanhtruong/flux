from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BudgetSet(BaseModel):
    user_id: str
    category: str
    monthly_limit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BudgetOut(BaseModel):
    id: UUID
    user_id: str
    category: str
    monthly_limit: Decimal
