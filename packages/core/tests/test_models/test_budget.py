import pytest
from decimal import Decimal
from pydantic import ValidationError
from flux_core.models.budget import BudgetSet


def test_valid_budget():
    b = BudgetSet(user_id="tg:12345", category="Food", monthly_limit=Decimal("500"))
    assert b.monthly_limit == Decimal("500")


def test_budget_limit_must_be_positive():
    with pytest.raises(ValidationError):
        BudgetSet(user_id="tg:12345", category="Food", monthly_limit=Decimal("0"))
