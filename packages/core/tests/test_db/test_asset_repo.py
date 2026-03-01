from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from flux_core.db.asset_repo import AssetRepository
from flux_core.db.connection import Database
from flux_core.migrations.migrate import migrate
from flux_core.models.asset import AssetCreate, AssetFrequency, AssetType


@pytest.fixture
async def db(pg_url):
    await migrate(pg_url)
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def user_id(db):
    uid = "test:asset_user"
    await db.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3)"
        " ON CONFLICT DO NOTHING",
        uid, "Asset User", "test",
    )
    return uid


@pytest.fixture
def repo(db):
    return AssetRepository(db)


async def test_create_income_asset(repo, user_id):
    asset = AssetCreate(
        user_id=user_id,
        name="Salary",
        amount=Decimal("5000.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
    )
    result = await repo.create(asset)
    assert result.name == "Salary"
    assert result.asset_type == AssetType.income
    assert result.principal_amount is None
    assert result.active is True


async def test_create_savings_asset(repo, user_id):
    asset = AssetCreate(
        user_id=user_id,
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
    result = await repo.create(asset)
    assert result.name == "Fixed Deposit"
    assert result.asset_type == AssetType.savings
    assert result.principal_amount == Decimal("10000.00")
    assert result.compound_frequency == "quarterly"
    assert result.maturity_date == date(2027, 6, 1)
    assert result.start_date == date(2026, 3, 1)
    assert result.frequency == AssetFrequency.quarterly


async def test_get_asset(repo, user_id):
    created = await repo.create(AssetCreate(
        user_id=user_id,
        name="Rental Income",
        amount=Decimal("2000.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
    ))
    result = await repo.get(created.id, user_id)
    assert result is not None
    assert result.id == created.id
    assert result.name == "Rental Income"


async def test_get_asset_not_found(repo, user_id):
    result = await repo.get(uuid4(), user_id)
    assert result is None


async def test_get_asset_wrong_user(repo, user_id):
    created = await repo.create(AssetCreate(
        user_id=user_id,
        name="My Asset",
        amount=Decimal("1000.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
    ))
    result = await repo.get(created.id, "other:user")
    assert result is None


async def test_list_by_user_with_asset_type_filter(repo, user_id):
    await repo.create(AssetCreate(
        user_id=user_id,
        name="Salary Filter",
        amount=Decimal("5000.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
        asset_type=AssetType.income,
    ))
    await repo.create(AssetCreate(
        user_id=user_id,
        name="FD Filter",
        amount=Decimal("10000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.quarterly,
        next_date=date(2026, 6, 1),
        category="Savings",
        asset_type=AssetType.savings,
        principal_amount=Decimal("10000.00"),
    ))

    savings = await repo.list_by_user(user_id, asset_type="savings")
    assert all(a.asset_type == AssetType.savings for a in savings)
    assert any(a.name == "FD Filter" for a in savings)

    income = await repo.list_by_user(user_id, asset_type="income")
    assert all(a.asset_type == AssetType.income for a in income)
    assert any(a.name == "Salary Filter" for a in income)

    # No filter returns all
    all_assets = await repo.list_by_user(user_id)
    assert len(all_assets) >= 2


async def test_update_amount(repo, user_id):
    created = await repo.create(AssetCreate(
        user_id=user_id,
        name="Growing FD",
        amount=Decimal("10000.00"),
        frequency=AssetFrequency.quarterly,
        next_date=date(2026, 6, 1),
        category="Savings",
        asset_type=AssetType.savings,
        principal_amount=Decimal("10000.00"),
    ))
    updated = await repo.update_amount(created.id, user_id, Decimal("10125.00"))
    assert updated is not None
    assert updated.amount == Decimal("10125.00")
    assert updated.name == "Growing FD"


async def test_deactivate(repo, user_id):
    created = await repo.create(AssetCreate(
        user_id=user_id,
        name="To Deactivate",
        amount=Decimal("1000.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Income",
    ))
    assert created.active is True

    result = await repo.deactivate(created.id, user_id)
    assert result is not None
    assert result.active is False

    # Should not appear in active-only listing
    active = await repo.list_by_user(user_id)
    assert all(a.id != created.id for a in active)
