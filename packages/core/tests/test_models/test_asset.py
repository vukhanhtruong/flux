from datetime import date
from decimal import Decimal
from uuid import uuid4

from flux_core.models.asset import AssetCreate, AssetFrequency, AssetOut, AssetType


def test_asset_type_enum_values():
    assert AssetType.income == "income"
    assert AssetType.savings == "savings"


def test_asset_frequency_quarterly():
    assert AssetFrequency.quarterly == "quarterly"


def test_asset_create_income_defaults():
    """Backward compat: existing callers omitting new fields still work."""
    asset = AssetCreate(
        user_id="test:user",
        name="Salary",
        amount=Decimal("5000.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
    )
    assert asset.asset_type == AssetType.income
    assert asset.principal_amount is None
    assert asset.compound_frequency is None
    assert asset.maturity_date is None
    assert asset.start_date is None


def test_asset_create_savings_fields():
    asset = AssetCreate(
        user_id="test:user",
        name="Fixed Deposit",
        amount=Decimal("10000.00"),
        interest_rate=Decimal("5.50"),
        frequency=AssetFrequency.quarterly,
        next_date=date(2026, 6, 1),
        category="Savings",
        asset_type=AssetType.savings,
        principal_amount=Decimal("10000.00"),
        compound_frequency="quarterly",
        maturity_date=date(2027, 6, 1),
        start_date=date(2026, 3, 1),
    )
    assert asset.asset_type == AssetType.savings
    assert asset.principal_amount == Decimal("10000.00")
    assert asset.compound_frequency == "quarterly"
    assert asset.maturity_date == date(2027, 6, 1)
    assert asset.start_date == date(2026, 3, 1)


def test_asset_out_savings_fields():
    asset = AssetOut(
        id=uuid4(),
        user_id="test:user",
        name="Fixed Deposit",
        amount=Decimal("10000.00"),
        interest_rate=Decimal("5.50"),
        frequency=AssetFrequency.quarterly,
        next_date=date(2026, 6, 1),
        category="Savings",
        active=True,
        asset_type=AssetType.savings,
        principal_amount=Decimal("10000.00"),
        compound_frequency="quarterly",
        maturity_date=date(2027, 6, 1),
        start_date=date(2026, 3, 1),
    )
    assert asset.asset_type == AssetType.savings
    assert asset.principal_amount == Decimal("10000.00")


def test_asset_out_income_defaults():
    """Backward compat: AssetOut without new fields uses defaults."""
    asset = AssetOut(
        id=uuid4(),
        user_id="test:user",
        name="Salary",
        amount=Decimal("5000.00"),
        interest_rate=Decimal("0"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
        active=True,
    )
    assert asset.asset_type == AssetType.income
    assert asset.principal_amount is None
    assert asset.compound_frequency is None
    assert asset.maturity_date is None
    assert asset.start_date is None
