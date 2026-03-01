# Savings with Interest — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add savings deposit tracking with compound interest to the assets system, with automated interest application via the scheduler.

**Architecture:** Extend the existing `assets` table with savings-specific columns (`asset_type`, `principal_amount`, `compound_frequency`, `maturity_date`, `start_date`). Add a `SavingsSchedulerRepo` (mirroring `SubscriptionSchedulerRepo`) to manage scheduler tasks paired to savings assets. Add new core business logic functions for interest calculation and savings lifecycle management. Wire everything through MCP tools.

**Tech Stack:** Python 3.12, asyncpg, Pydantic v2, FastMCP, pytest, testcontainers

**Design doc:** `docs/plans/2026-03-01-savings-interest-design.md`

---

## Task 1: Database Migration — Add Savings Columns to Assets Table

**Files:**
- Create: `packages/core/src/flux_core/migrations/005_asset_savings.sql`

**Step 1: Write the migration SQL**

```sql
ALTER TABLE assets ADD COLUMN asset_type TEXT NOT NULL DEFAULT 'income'
    CHECK (asset_type IN ('income', 'savings'));
ALTER TABLE assets ADD COLUMN principal_amount NUMERIC(12,2);
ALTER TABLE assets ADD COLUMN compound_frequency TEXT
    CHECK (compound_frequency IN ('monthly', 'quarterly', 'yearly'));
ALTER TABLE assets ADD COLUMN maturity_date DATE;
ALTER TABLE assets ADD COLUMN start_date DATE;
```

**Step 2: Verify migration applies cleanly**

Run: `cd packages/core && python -c "from flux_core.migrations.migrate import migrate; import asyncio; asyncio.run(migrate('postgresql://localhost/flux'))"`

If no local DB is available, skip — integration tests in Task 4 will exercise this.

**Step 3: Commit**

```bash
git add packages/core/src/flux_core/migrations/005_asset_savings.sql
git commit -m "feat: add savings columns to assets table (migration 005)"
```

---

## Task 2: Update Pydantic Models — AssetType, AssetFrequency, AssetCreate, AssetOut

**Files:**
- Modify: `packages/core/src/flux_core/models/asset.py`
- Test: `packages/core/tests/test_models/test_asset.py` (create new)

**Step 1: Write failing tests for the new model fields**

Create `packages/core/tests/test_models/test_asset.py`:

```python
from datetime import date
from decimal import Decimal
import pytest
from flux_core.models.asset import (
    AssetCreate, AssetOut, AssetFrequency, AssetType,
)


def test_asset_type_enum():
    assert AssetType.income == "income"
    assert AssetType.savings == "savings"


def test_asset_frequency_quarterly():
    assert AssetFrequency.quarterly == "quarterly"


def test_asset_create_income_defaults():
    """Regular income asset works with defaults (backward compatible)."""
    asset = AssetCreate(
        user_id="tg:123",
        name="Salary",
        amount=Decimal("5000.00"),
        frequency="monthly",
        next_date=date(2026, 3, 1),
        category="Income",
    )
    assert asset.asset_type == AssetType.income
    assert asset.principal_amount is None
    assert asset.compound_frequency is None
    assert asset.maturity_date is None
    assert asset.start_date is None


def test_asset_create_savings():
    """Savings asset with all fields populated."""
    asset = AssetCreate(
        user_id="tg:123",
        name="Bank Savings",
        amount=Decimal("100000000.00"),
        interest_rate=Decimal("5.00"),
        frequency="yearly",
        next_date=date(2027, 3, 1),
        category="Savings",
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency="yearly",
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    assert asset.asset_type == AssetType.savings
    assert asset.principal_amount == Decimal("100000000.00")
    assert asset.compound_frequency == AssetFrequency.yearly
    assert asset.maturity_date == date(2029, 3, 1)
    assert asset.start_date == date(2026, 3, 1)


def test_asset_create_savings_quarterly():
    """Savings with quarterly compounding."""
    asset = AssetCreate(
        user_id="tg:123",
        name="CD",
        amount=Decimal("50000000.00"),
        interest_rate=Decimal("4.50"),
        frequency="quarterly",
        next_date=date(2026, 6, 1),
        category="Savings",
        asset_type="savings",
        principal_amount=Decimal("50000000.00"),
        compound_frequency="quarterly",
        maturity_date=date(2028, 3, 1),
        start_date=date(2026, 3, 1),
    )
    assert asset.compound_frequency == AssetFrequency.quarterly


def test_asset_out_includes_savings_fields():
    """AssetOut model includes all savings fields."""
    from uuid import UUID
    asset = AssetOut(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        user_id="tg:123",
        name="Bank Savings",
        amount=Decimal("105000000.00"),
        interest_rate=Decimal("5.00"),
        frequency="yearly",
        next_date=date(2028, 3, 1),
        category="Savings",
        active=True,
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency="yearly",
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    assert asset.asset_type == AssetType.savings
    assert asset.principal_amount == Decimal("100000000.00")


def test_asset_out_income_defaults():
    """AssetOut for regular income assets has None savings fields."""
    from uuid import UUID
    asset = AssetOut(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        user_id="tg:123",
        name="Salary",
        amount=Decimal("5000.00"),
        interest_rate=Decimal("0"),
        frequency="monthly",
        next_date=date(2026, 3, 1),
        category="Income",
        active=True,
    )
    assert asset.asset_type == AssetType.income
    assert asset.principal_amount is None
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_models/test_asset.py -v`

Expected: FAIL — `AssetType` doesn't exist, `quarterly` not in `AssetFrequency`, new fields missing.

**Step 3: Implement model changes**

Modify `packages/core/src/flux_core/models/asset.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && pytest tests/test_models/test_asset.py -v`

Expected: All PASS.

**Step 5: Run existing asset tests to confirm backward compatibility**

Run: `cd packages/core && pytest tests/test_tools/test_financial_tools.py::test_create_asset tests/test_tools/test_financial_tools.py::test_list_assets -v`

Expected: All PASS — existing tests don't provide `asset_type` so defaults apply.

**Step 6: Commit**

```bash
git add packages/core/src/flux_core/models/asset.py packages/core/tests/test_models/test_asset.py
git commit -m "feat: add AssetType enum and savings fields to asset models"
```

---

## Task 3: Update AssetRepository — New Columns, get(), update_amount(), deactivate()

**Files:**
- Modify: `packages/core/src/flux_core/db/asset_repo.py`
- Test: `packages/core/tests/test_db/test_asset_repo.py` (create new)

**Step 1: Write failing integration tests**

Create `packages/core/tests/test_db/test_asset_repo.py`:

```python
import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from flux_core.db.connection import Database
from flux_core.db.asset_repo import AssetRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.asset import AssetCreate, AssetType, AssetFrequency


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
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) "
        "ON CONFLICT DO NOTHING",
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
        frequency="monthly",
        next_date=date(2026, 3, 1),
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
        name="Bank Savings",
        amount=Decimal("100000000.00"),
        interest_rate=Decimal("5.00"),
        frequency="yearly",
        next_date=date(2027, 3, 1),
        category="Savings",
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency="yearly",
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    result = await repo.create(asset)
    assert result.name == "Bank Savings"
    assert result.asset_type == AssetType.savings
    assert result.principal_amount == Decimal("100000000.00")
    assert result.compound_frequency == AssetFrequency.yearly
    assert result.maturity_date == date(2029, 3, 1)
    assert result.start_date == date(2026, 3, 1)


async def test_get_asset(repo, user_id):
    asset = AssetCreate(
        user_id=user_id,
        name="TestGet",
        amount=Decimal("1000.00"),
        frequency="monthly",
        next_date=date(2026, 3, 1),
        category="Test",
    )
    created = await repo.create(asset)
    result = await repo.get(created.id, user_id)
    assert result is not None
    assert result.id == created.id
    assert result.name == "TestGet"


async def test_get_asset_not_found(repo, user_id):
    result = await repo.get(uuid4(), user_id)
    assert result is None


async def test_get_asset_wrong_user(repo, user_id):
    asset = AssetCreate(
        user_id=user_id,
        name="Mine",
        amount=Decimal("1000.00"),
        frequency="monthly",
        next_date=date(2026, 3, 1),
        category="Test",
    )
    created = await repo.create(asset)
    result = await repo.get(created.id, "other:user")
    assert result is None


async def test_list_by_user_with_asset_type_filter(repo, user_id):
    await repo.create(AssetCreate(
        user_id=user_id, name="Salary", amount=Decimal("5000.00"),
        frequency="monthly", next_date=date(2026, 3, 1), category="Income",
    ))
    await repo.create(AssetCreate(
        user_id=user_id, name="Savings", amount=Decimal("100000.00"),
        interest_rate=Decimal("5.00"), frequency="yearly",
        next_date=date(2027, 3, 1), category="Savings",
        asset_type="savings", principal_amount=Decimal("100000.00"),
        compound_frequency="yearly", maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    ))

    all_assets = await repo.list_by_user(user_id)
    savings_only = await repo.list_by_user(user_id, asset_type="savings")
    income_only = await repo.list_by_user(user_id, asset_type="income")

    assert len(savings_only) >= 1
    assert all(a.asset_type == AssetType.savings for a in savings_only)
    assert len(income_only) >= 1
    assert all(a.asset_type == AssetType.income for a in income_only)
    assert len(all_assets) >= len(savings_only) + len(income_only)


async def test_update_amount(repo, user_id):
    asset = AssetCreate(
        user_id=user_id, name="Savings", amount=Decimal("100000000.00"),
        interest_rate=Decimal("5.00"), frequency="yearly",
        next_date=date(2027, 3, 1), category="Savings",
        asset_type="savings", principal_amount=Decimal("100000000.00"),
        compound_frequency="yearly", maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    created = await repo.create(asset)

    result = await repo.update_amount(created.id, user_id, Decimal("105000000.00"))
    assert result is not None
    assert result.amount == Decimal("105000000.00")


async def test_deactivate(repo, user_id):
    asset = AssetCreate(
        user_id=user_id, name="Deactivate Me", amount=Decimal("1000.00"),
        frequency="monthly", next_date=date(2026, 3, 1), category="Test",
    )
    created = await repo.create(asset)
    assert created.active is True

    result = await repo.deactivate(created.id, user_id)
    assert result is not None
    assert result.active is False
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_db/test_asset_repo.py -v`

Expected: FAIL — `get()`, `update_amount()`, `deactivate()` don't exist, `list_by_user` doesn't accept `asset_type`, `_COLUMNS` missing new columns.

**Step 3: Update the repository**

Modify `packages/core/src/flux_core/db/asset_repo.py`:

```python
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.asset import AssetCreate, AssetOut


class AssetRepository:
    def __init__(self, db: Database):
        self._db = db

    _COLUMNS = (
        "id, user_id, name, amount, interest_rate, frequency, next_date, "
        "category, active, asset_type, principal_amount, compound_frequency, "
        "maturity_date, start_date"
    )

    async def create(self, asset: AssetCreate) -> AssetOut:
        row = await self._db.fetchrow(
            f"""
            INSERT INTO assets (user_id, name, amount, interest_rate, frequency,
                next_date, category, asset_type, principal_amount,
                compound_frequency, maturity_date, start_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING {self._COLUMNS}
            """,
            asset.user_id, asset.name, asset.amount, asset.interest_rate,
            asset.frequency.value, asset.next_date, asset.category,
            asset.asset_type.value, asset.principal_amount,
            asset.compound_frequency.value if asset.compound_frequency else None,
            asset.maturity_date, asset.start_date,
        )
        return AssetOut(**dict(row))

    async def get(self, asset_id: UUID, user_id: str) -> Optional[AssetOut]:
        row = await self._db.fetchrow(
            f"SELECT {self._COLUMNS} FROM assets WHERE id = $1 AND user_id = $2",
            asset_id, user_id,
        )
        return AssetOut(**dict(row)) if row else None

    async def list_by_user(
        self, user_id: str, active_only: bool = True, asset_type: Optional[str] = None,
    ) -> list[AssetOut]:
        condition = "user_id = $1"
        params: list = [user_id]
        if active_only:
            condition += " AND active = TRUE"
        if asset_type:
            params.append(asset_type)
            condition += f" AND asset_type = ${len(params)}"
        rows = await self._db.fetch(
            f"SELECT {self._COLUMNS} FROM assets WHERE {condition} ORDER BY next_date",
            *params,
        )
        return [AssetOut(**dict(r)) for r in rows]

    async def get_due(self, user_id: str, as_of: date) -> list[AssetOut]:
        rows = await self._db.fetch(
            f"""
            SELECT {self._COLUMNS} FROM assets
            WHERE user_id = $1 AND active = TRUE AND next_date <= $2
            ORDER BY next_date
            """,
            user_id, as_of,
        )
        return [AssetOut(**dict(r)) for r in rows]

    async def advance_next_date(self, asset_id: UUID, user_id: str) -> Optional[AssetOut]:
        row = await self._db.fetchrow(
            f"""
            UPDATE assets SET next_date = CASE
                WHEN frequency = 'monthly' THEN next_date + INTERVAL '1 month'
                WHEN frequency = 'quarterly' THEN next_date + INTERVAL '3 months'
                WHEN frequency = 'yearly' THEN next_date + INTERVAL '1 year'
            END
            WHERE id = $1 AND user_id = $2
            RETURNING {self._COLUMNS}
            """,
            asset_id, user_id,
        )
        return AssetOut(**dict(row)) if row else None

    async def update_amount(
        self, asset_id: UUID, user_id: str, new_amount: Decimal,
    ) -> Optional[AssetOut]:
        row = await self._db.fetchrow(
            f"""
            UPDATE assets SET amount = $3
            WHERE id = $1 AND user_id = $2
            RETURNING {self._COLUMNS}
            """,
            asset_id, user_id, new_amount,
        )
        return AssetOut(**dict(row)) if row else None

    async def deactivate(self, asset_id: UUID, user_id: str) -> Optional[AssetOut]:
        row = await self._db.fetchrow(
            f"""
            UPDATE assets SET active = FALSE
            WHERE id = $1 AND user_id = $2
            RETURNING {self._COLUMNS}
            """,
            asset_id, user_id,
        )
        return AssetOut(**dict(row)) if row else None

    async def delete(self, asset_id: UUID, user_id: str) -> bool:
        result = await self._db.execute(
            "DELETE FROM assets WHERE id = $1 AND user_id = $2", asset_id, user_id,
        )
        return result == "DELETE 1"
```

**Step 4: Run tests to verify they pass**

Run: `cd packages/core && pytest tests/test_db/test_asset_repo.py -v`

Expected: All PASS.

**Step 5: Run existing asset tool tests to confirm backward compatibility**

Run: `cd packages/core && pytest tests/test_tools/test_financial_tools.py::test_create_asset tests/test_tools/test_financial_tools.py::test_list_assets -v`

Expected: All PASS.

**Step 6: Commit**

```bash
git add packages/core/src/flux_core/db/asset_repo.py packages/core/tests/test_db/test_asset_repo.py
git commit -m "feat: update AssetRepository with savings columns, get(), update_amount(), deactivate()"
```

---

## Task 4: Core Business Logic — Savings Tools (create, process interest, list, close)

**Files:**
- Modify: `packages/core/src/flux_core/tools/financial_tools.py`
- Test: `packages/core/tests/test_tools/test_financial_tools.py` (append)

**Step 1: Write failing tests for savings business logic**

Append to `packages/core/tests/test_tools/test_financial_tools.py`. Add these imports at top:

```python
from flux_core.tools.financial_tools import (
    # ... existing imports ...
    create_savings_deposit,
    process_savings_interest,
    list_savings,
    close_savings_early,
)
```

Then append these tests at the end of the file:

```python
# Savings tests

@pytest.mark.asyncio
async def test_create_savings_deposit():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = AssetOut(
        id=test_uuid,
        user_id="test_user",
        name="Bank Savings",
        amount=Decimal("100000000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 3, 1),
        category="Savings",
        active=True,
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )

    result = await create_savings_deposit(
        user_id="test_user",
        name="Bank Savings",
        amount=100000000.0,
        interest_rate=5.0,
        compound_frequency="yearly",
        start_date="2026-03-01",
        maturity_date="2029-03-01",
        category="Savings",
        repo=mock_repo,
    )

    assert result["id"] == str(test_uuid)
    assert result["asset_type"] == "savings"
    assert result["principal_amount"] == "100000000.00"
    assert result["maturity_date"] == "2029-03-01"
    mock_repo.create.assert_called_once()
    call_args = mock_repo.create.call_args[0][0]
    assert call_args.asset_type.value == "savings"
    assert call_args.principal_amount == Decimal("100000000.00")


@pytest.mark.asyncio
async def test_process_savings_interest_annual():
    """100M at 5%/year annual compound — first year produces 5M interest."""
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.get.return_value = AssetOut(
        id=test_uuid,
        user_id="test_user",
        name="Bank Savings",
        amount=Decimal("100000000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 3, 1),
        category="Savings",
        active=True,
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    mock_repo.update_amount.return_value = AssetOut(
        id=test_uuid,
        user_id="test_user",
        name="Bank Savings",
        amount=Decimal("105000000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly,
        next_date=date(2028, 3, 1),
        category="Savings",
        active=True,
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    mock_repo.advance_next_date.return_value = mock_repo.update_amount.return_value

    result = await process_savings_interest(
        asset_id=str(test_uuid),
        user_id="test_user",
        repo=mock_repo,
    )

    assert result["interest_applied"] == "5000000.00"
    assert result["new_balance"] == "105000000.00"
    assert result["matured"] is False
    mock_repo.update_amount.assert_called_once_with(
        test_uuid, "test_user", Decimal("105000000.00"),
    )
    mock_repo.advance_next_date.assert_called_once()


@pytest.mark.asyncio
async def test_process_savings_interest_monthly():
    """100M at 5%/year monthly compound — first month produces ~416,666.67."""
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.get.return_value = AssetOut(
        id=test_uuid,
        user_id="test_user",
        name="Bank Savings",
        amount=Decimal("100000000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.monthly,
        next_date=date(2026, 4, 1),
        category="Savings",
        active=True,
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.monthly,
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    # interest = 100M * (5 / 100 / 12) = 416666.67
    new_amount = Decimal("100000000.00") + Decimal("416666.67")
    mock_repo.update_amount.return_value = AssetOut(
        id=test_uuid, user_id="test_user", name="Bank Savings",
        amount=new_amount, interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.monthly, next_date=date(2026, 5, 1),
        category="Savings", active=True, asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.monthly,
        maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
    )
    mock_repo.advance_next_date.return_value = mock_repo.update_amount.return_value

    result = await process_savings_interest(
        asset_id=str(test_uuid), user_id="test_user", repo=mock_repo,
    )

    assert result["interest_applied"] == "416666.67"
    assert result["matured"] is False


@pytest.mark.asyncio
async def test_process_savings_interest_maturity():
    """Last interest application triggers maturity."""
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    # This is the final compounding — next_date will be 2029-03-01 which is maturity_date
    mock_repo.get.return_value = AssetOut(
        id=test_uuid,
        user_id="test_user",
        name="Bank Savings",
        amount=Decimal("110250000.00"),
        interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly,
        next_date=date(2029, 3, 1),
        category="Savings",
        active=True,
        asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1),
        start_date=date(2026, 3, 1),
    )
    new_amount = Decimal("110250000.00") + Decimal("5512500.00")
    mock_repo.update_amount.return_value = AssetOut(
        id=test_uuid, user_id="test_user", name="Bank Savings",
        amount=new_amount, interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly, next_date=date(2029, 3, 1),
        category="Savings", active=True, asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
    )
    mock_repo.deactivate.return_value = AssetOut(
        id=test_uuid, user_id="test_user", name="Bank Savings",
        amount=new_amount, interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly, next_date=date(2029, 3, 1),
        category="Savings", active=False, asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
    )

    result = await process_savings_interest(
        asset_id=str(test_uuid), user_id="test_user", repo=mock_repo,
    )

    assert result["matured"] is True
    assert "115762500" in result["new_balance"]
    mock_repo.deactivate.assert_called_once_with(test_uuid, "test_user")


@pytest.mark.asyncio
async def test_process_savings_interest_inactive_raises():
    """Processing interest on an inactive savings raises ValueError."""
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.get.return_value = AssetOut(
        id=test_uuid, user_id="test_user", name="Old Savings",
        amount=Decimal("100000.00"), interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly, next_date=date(2027, 3, 1),
        category="Savings", active=False, asset_type="savings",
        principal_amount=Decimal("100000.00"), compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
    )

    with pytest.raises(ValueError, match="not active"):
        await process_savings_interest(
            asset_id=str(test_uuid), user_id="test_user", repo=mock_repo,
        )


@pytest.mark.asyncio
async def test_process_savings_interest_not_found_raises():
    mock_repo = AsyncMock()
    mock_repo.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await process_savings_interest(
            asset_id="nonexistent", user_id="test_user", repo=mock_repo,
        )


@pytest.mark.asyncio
async def test_list_savings():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        AssetOut(
            id=test_uuid, user_id="test_user", name="Bank Savings",
            amount=Decimal("105000000.00"), interest_rate=Decimal("5.00"),
            frequency=AssetFrequency.yearly, next_date=date(2028, 3, 1),
            category="Savings", active=True, asset_type="savings",
            principal_amount=Decimal("100000000.00"),
            compound_frequency=AssetFrequency.yearly,
            maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
        )
    ]

    result = await list_savings(user_id="test_user", repo=mock_repo)

    assert len(result) == 1
    assert result[0]["name"] == "Bank Savings"
    assert result[0]["principal_amount"] == "100000000.00"
    assert result[0]["interest_earned"] == "5000000.00"
    mock_repo.list_by_user.assert_called_once_with("test_user", True, asset_type="savings")


@pytest.mark.asyncio
async def test_close_savings_early():
    mock_repo = AsyncMock()
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.get.return_value = AssetOut(
        id=test_uuid, user_id="test_user", name="Bank Savings",
        amount=Decimal("105000000.00"), interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly, next_date=date(2028, 3, 1),
        category="Savings", active=True, asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
    )
    mock_repo.deactivate.return_value = AssetOut(
        id=test_uuid, user_id="test_user", name="Bank Savings",
        amount=Decimal("105000000.00"), interest_rate=Decimal("5.00"),
        frequency=AssetFrequency.yearly, next_date=date(2028, 3, 1),
        category="Savings", active=False, asset_type="savings",
        principal_amount=Decimal("100000000.00"),
        compound_frequency=AssetFrequency.yearly,
        maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
    )

    result = await close_savings_early(
        asset_id=str(test_uuid), user_id="test_user", repo=mock_repo,
    )

    assert result["active"] is False
    assert result["name"] == "Bank Savings"
    mock_repo.deactivate.assert_called_once_with(test_uuid, "test_user")
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/core && pytest tests/test_tools/test_financial_tools.py -k savings -v`

Expected: FAIL — functions don't exist yet.

**Step 3: Implement savings business logic**

Append to `packages/core/src/flux_core/tools/financial_tools.py`:

```python
# Savings tools

COMPOUND_PERIODS = {"monthly": 12, "quarterly": 4, "yearly": 1}


async def create_savings_deposit(
    user_id: str,
    name: str,
    amount: float,
    interest_rate: float,
    compound_frequency: str,
    start_date: str,
    maturity_date: str,
    category: str,
    repo: AssetRepository,
) -> dict:
    """Create a new savings deposit with compound interest."""
    freq = AssetFrequency(compound_frequency)
    start = _date.fromisoformat(start_date)

    # next_date = first interest application date (one compounding period after start)
    if freq == AssetFrequency.monthly:
        next_dt = _date(start.year + (start.month // 12), (start.month % 12) + 1, start.day)
    elif freq == AssetFrequency.quarterly:
        m = start.month + 3
        next_dt = _date(start.year + (m - 1) // 12, ((m - 1) % 12) + 1, start.day)
    else:  # yearly
        next_dt = _date(start.year + 1, start.month, start.day)

    asset = AssetCreate(
        user_id=user_id,
        name=name,
        amount=Decimal(str(amount)),
        interest_rate=Decimal(str(interest_rate)),
        frequency=freq,
        next_date=next_dt,
        category=category,
        asset_type=AssetType.savings,
        principal_amount=Decimal(str(amount)),
        compound_frequency=freq,
        maturity_date=_date.fromisoformat(maturity_date),
        start_date=start,
    )
    result = await repo.create(asset)
    return _savings_to_dict(result)


async def process_savings_interest(
    asset_id: str,
    user_id: str,
    repo: AssetRepository,
) -> dict:
    """Calculate and apply compound interest for a savings asset.

    Called by the scheduler at each compounding period.
    Updates the asset balance and checks for maturity.
    """
    from uuid import UUID as _UUID
    aid = _UUID(asset_id)
    asset = await repo.get(aid, user_id)
    if asset is None:
        raise ValueError(f"Savings asset {asset_id} not found")
    if not asset.active:
        raise ValueError(f"Savings asset {asset_id} is not active")

    periods = COMPOUND_PERIODS[asset.compound_frequency.value]
    interest = (asset.amount * asset.interest_rate / 100 / periods).quantize(Decimal("0.01"))
    new_amount = asset.amount + interest

    await repo.update_amount(aid, user_id, new_amount)
    await repo.advance_next_date(aid, user_id)

    # Check maturity: if next_date >= maturity_date, this was the last period
    matured = asset.next_date >= asset.maturity_date
    if matured:
        await repo.deactivate(aid, user_id)

    return {
        "asset_id": asset_id,
        "name": asset.name,
        "interest_applied": str(interest),
        "new_balance": str(new_amount),
        "matured": matured,
        "maturity_message": (
            f"Your savings '{asset.name}' has matured! "
            f"Final balance: {new_amount} "
            f"(started at {asset.principal_amount} on {asset.start_date}). "
            f"The savings has been deactivated."
        ) if matured else None,
    }


async def list_savings(
    user_id: str,
    repo: AssetRepository,
    active_only: bool = True,
) -> list[dict]:
    """List all savings deposits for a user."""
    assets = await repo.list_by_user(user_id, active_only, asset_type="savings")
    result = []
    for a in assets:
        d = _savings_to_dict(a)
        d["interest_earned"] = str(a.amount - a.principal_amount)
        result.append(d)
    return result


async def close_savings_early(
    asset_id: str,
    user_id: str,
    repo: AssetRepository,
) -> dict:
    """Close a savings deposit before maturity."""
    from uuid import UUID as _UUID
    aid = _UUID(asset_id)
    asset = await repo.get(aid, user_id)
    if asset is None:
        raise ValueError(f"Savings asset {asset_id} not found")
    if not asset.active:
        raise ValueError(f"Savings asset {asset_id} is already inactive")

    result = await repo.deactivate(aid, user_id)
    return _savings_to_dict(result)


def _savings_to_dict(a: AssetOut) -> dict:
    """Convert an AssetOut (savings type) to a response dict."""
    return {
        "id": str(a.id),
        "user_id": a.user_id,
        "name": a.name,
        "amount": str(a.amount),
        "interest_rate": str(a.interest_rate),
        "frequency": a.frequency.value,
        "next_date": str(a.next_date),
        "category": a.category,
        "active": a.active,
        "asset_type": a.asset_type.value,
        "principal_amount": str(a.principal_amount),
        "compound_frequency": a.compound_frequency.value if a.compound_frequency else None,
        "maturity_date": str(a.maturity_date) if a.maturity_date else None,
        "start_date": str(a.start_date) if a.start_date else None,
    }
```

Also add missing imports at the top of `financial_tools.py`:

```python
from flux_core.models.asset import AssetCreate, AssetFrequency, AssetType, AssetOut
```

(Replace the existing `from flux_core.models.asset import AssetCreate, AssetFrequency` line.)

**Step 4: Run all tests to verify they pass**

Run: `cd packages/core && pytest tests/test_tools/test_financial_tools.py -v`

Expected: All PASS (both existing and new tests).

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/tools/financial_tools.py packages/core/tests/test_tools/test_financial_tools.py
git commit -m "feat: add savings deposit business logic (create, process interest, list, close)"
```

---

## Task 5: Update Existing Asset Tool Output — Include Savings Fields

The existing `create_asset`, `list_assets`, `advance_asset`, `delete_asset` functions output dicts that don't include the new savings fields. Update them to include `asset_type` and savings fields so the MCP layer can display them properly.

**Files:**
- Modify: `packages/core/src/flux_core/tools/financial_tools.py`
- Test: `packages/core/tests/test_tools/test_financial_tools.py` (update existing tests)

**Step 1: Update `_asset_to_dict` helper and existing functions**

Add a helper function in `financial_tools.py` and update `create_asset`, `list_assets`, `advance_asset`:

```python
def _asset_to_dict(a: AssetOut) -> dict:
    """Convert an AssetOut to a response dict (works for both income and savings)."""
    d = {
        "id": str(a.id),
        "user_id": a.user_id,
        "name": a.name,
        "amount": str(a.amount),
        "interest_rate": str(a.interest_rate),
        "frequency": a.frequency.value,
        "next_date": str(a.next_date),
        "category": a.category,
        "active": a.active,
        "asset_type": a.asset_type.value,
    }
    if a.asset_type == AssetType.savings:
        d["principal_amount"] = str(a.principal_amount) if a.principal_amount else None
        d["compound_frequency"] = a.compound_frequency.value if a.compound_frequency else None
        d["maturity_date"] = str(a.maturity_date) if a.maturity_date else None
        d["start_date"] = str(a.start_date) if a.start_date else None
    return d
```

Then replace the inline dict creation in `create_asset`, `list_assets`, `advance_asset` with `_asset_to_dict(result)`.

Also update `_savings_to_dict` to call `_asset_to_dict` to avoid duplication.

**Step 2: Update existing tests to assert `asset_type` field**

In `test_create_asset`, add:
```python
assert result["asset_type"] == "income"
```

In `test_list_assets`, add:
```python
assert result[0]["asset_type"] == "income"
```

**Step 3: Run tests**

Run: `cd packages/core && pytest tests/test_tools/test_financial_tools.py -v`

Expected: All PASS.

**Step 4: Commit**

```bash
git add packages/core/src/flux_core/tools/financial_tools.py packages/core/tests/test_tools/test_financial_tools.py
git commit -m "refactor: unify asset dict output with _asset_to_dict helper"
```

---

## Task 6: SavingsSchedulerRepo — Manage Scheduler Tasks for Savings

**Files:**
- Create: `packages/mcp-server/src/flux_mcp/db/savings_scheduler_repo.py`
- Create: `packages/mcp-server/tests/test_tools/test_savings_lifecycle.py`

**Step 1: Write failing unit tests for savings scheduler lifecycle**

Create `packages/mcp-server/tests/test_tools/test_savings_lifecycle.py`:

```python
"""Unit tests for savings scheduler lifecycle hooks."""
from datetime import date, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID
import pytest

from flux_core.models.asset import AssetOut, AssetFrequency, AssetType
from flux_mcp.db.savings_scheduler_repo import SavingsSchedulerRepo, _derive_savings_cron


ASSET_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_ID = "tg:123"

_SAVINGS = AssetOut(
    id=ASSET_UUID, user_id=USER_ID, name="Bank Savings",
    amount=Decimal("100000000.00"), interest_rate=Decimal("5.00"),
    frequency=AssetFrequency.yearly, next_date=date(2027, 3, 1),
    category="Savings", active=True, asset_type=AssetType.savings,
    principal_amount=Decimal("100000000.00"),
    compound_frequency=AssetFrequency.yearly,
    maturity_date=date(2029, 3, 1), start_date=date(2026, 3, 1),
)


def test_derive_savings_cron_yearly():
    assert _derive_savings_cron(AssetFrequency.yearly, date(2027, 3, 1)) == "0 0 1 3 *"


def test_derive_savings_cron_monthly():
    assert _derive_savings_cron(AssetFrequency.monthly, date(2026, 4, 15)) == "0 0 15 * *"


def test_derive_savings_cron_quarterly():
    # Quarterly uses cron that fires every 3 months on the same day
    result = _derive_savings_cron(AssetFrequency.quarterly, date(2026, 6, 1))
    assert result == "0 0 1 3,6,9,12 *"


async def test_create_savings_with_scheduler():
    from flux_mcp.tools.savings_tools import _create_savings_with_scheduler

    asset_repo = AsyncMock()
    asset_repo.create.return_value = _SAVINGS
    scheduler_repo = AsyncMock()

    result = await _create_savings_with_scheduler(
        user_id=USER_ID,
        name="Bank Savings",
        amount=100000000.0,
        interest_rate=5.0,
        compound_frequency="yearly",
        start_date="2026-03-01",
        maturity_date="2029-03-01",
        category="Savings",
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["name"] == "Bank Savings"
    scheduler_repo.create.assert_called_once()
    call_kwargs = scheduler_repo.create.call_args.kwargs
    assert call_kwargs["cron"] == "0 0 1 3 *"
    assert call_kwargs["user_id"] == USER_ID


async def test_close_savings_deletes_scheduler():
    from flux_mcp.tools.savings_tools import _close_savings_with_scheduler

    asset_repo = AsyncMock()
    asset_repo.get.return_value = _SAVINGS
    asset_repo.deactivate.return_value = AssetOut(
        **{**_SAVINGS.model_dump(), "active": False}
    )
    scheduler_repo = AsyncMock()

    result = await _close_savings_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["active"] is False
    scheduler_repo.delete.assert_called_once_with(str(ASSET_UUID))
```

**Step 2: Run tests to verify they fail**

Run: `cd packages/mcp-server && pytest tests/test_tools/test_savings_lifecycle.py -v`

Expected: FAIL — module doesn't exist.

**Step 3: Implement SavingsSchedulerRepo**

Create `packages/mcp-server/src/flux_mcp/db/savings_scheduler_repo.py`:

```python
"""Manages bot_scheduled_tasks rows paired to savings assets."""
from datetime import date, datetime, timezone
from uuid import UUID

from flux_core.db.connection import Database
from flux_core.models.asset import AssetFrequency


def _derive_savings_cron(compound_frequency: AssetFrequency, next_date: date) -> str:
    """Derive a cron expression for savings interest compounding."""
    if compound_frequency == AssetFrequency.monthly:
        return f"0 0 {next_date.day} * *"
    if compound_frequency == AssetFrequency.quarterly:
        # Fire on same day in months that are 3 apart, starting from next_date.month
        start_month = next_date.month
        months = sorted(set((start_month + i * 3 - 1) % 12 + 1 for i in range(4)))
        return f"0 0 {next_date.day} {','.join(str(m) for m in months)} *"
    # yearly
    return f"0 0 {next_date.day} {next_date.month} *"


def _to_utc_midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


class SavingsSchedulerRepo:
    def __init__(self, db: Database):
        self._db = db

    async def create(
        self,
        user_id: str,
        asset_id: str,
        prompt: str,
        cron: str,
        next_run_at: datetime,
    ) -> int:
        """Insert a cron scheduler row paired to a savings asset. Returns task id."""
        row = await self._db.fetchrow(
            """
            INSERT INTO bot_scheduled_tasks
                (user_id, prompt, schedule_type, schedule_value, status, next_run_at, asset_id)
            VALUES ($1, $2, 'cron', $3, 'active', $4, $5)
            RETURNING id
            """,
            user_id, prompt, cron, next_run_at, UUID(asset_id),
        )
        return row["id"]

    async def pause(self, asset_id: str) -> None:
        await self._db.execute(
            "UPDATE bot_scheduled_tasks SET status = 'paused' WHERE asset_id = $1",
            UUID(asset_id),
        )

    async def resume(self, asset_id: str, next_run_at: datetime) -> None:
        await self._db.execute(
            """
            UPDATE bot_scheduled_tasks
            SET status = 'active', next_run_at = $2
            WHERE asset_id = $1
            """,
            UUID(asset_id), next_run_at,
        )

    async def delete(self, asset_id: str) -> None:
        await self._db.execute(
            "DELETE FROM bot_scheduled_tasks WHERE asset_id = $1",
            UUID(asset_id),
        )
```

**Step 4: Add `asset_id` column to `bot_scheduled_tasks`**

Create `packages/agent-bot/migrations/006_add_asset_id.sql`:

```sql
ALTER TABLE bot_scheduled_tasks
    ADD COLUMN IF NOT EXISTS asset_id UUID;

CREATE INDEX IF NOT EXISTS idx_bot_scheduled_asset
    ON bot_scheduled_tasks(asset_id)
    WHERE asset_id IS NOT NULL;
```

**Step 5: Implement MCP savings tools wrapper**

Create `packages/mcp-server/src/flux_mcp/tools/savings_tools.py`:

```python
import logging
from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.asset_repo import AssetRepository
from flux_core.models.asset import AssetFrequency
from flux_core.tools import financial_tools as biz
from flux_mcp.db.savings_scheduler_repo import (
    SavingsSchedulerRepo, _derive_savings_cron, _to_utc_midnight,
)


# ── testable helpers ────────────────────────────────────────────────────────

async def _create_savings_with_scheduler(
    user_id: str,
    name: str,
    amount: float,
    interest_rate: float,
    compound_frequency: str,
    start_date: str,
    maturity_date: str,
    category: str,
    asset_repo: AssetRepository,
    scheduler_repo: SavingsSchedulerRepo,
) -> dict:
    result = await biz.create_savings_deposit(
        user_id, name, amount, interest_rate, compound_frequency,
        start_date, maturity_date, category, asset_repo,
    )
    from datetime import date
    nd = date.fromisoformat(result["next_date"])
    freq = AssetFrequency(result["compound_frequency"])
    prompt = f"Process savings interest for {result['name']} (id: {result['id']})"
    try:
        await scheduler_repo.create(
            user_id=user_id,
            asset_id=result["id"],
            prompt=prompt,
            cron=_derive_savings_cron(freq, nd),
            next_run_at=_to_utc_midnight(nd),
        )
    except Exception as exc:
        logging.getLogger(__name__).error(
            "Failed to create scheduler for savings %s: %s", result["id"], exc
        )
    return result


async def _close_savings_with_scheduler(
    asset_id: str,
    user_id: str,
    asset_repo: AssetRepository,
    scheduler_repo: SavingsSchedulerRepo,
) -> dict:
    await scheduler_repo.delete(asset_id)
    return await biz.close_savings_early(asset_id, user_id, asset_repo)


async def _delete_savings_with_scheduler(
    asset_id: str,
    user_id: str,
    asset_repo: AssetRepository,
    scheduler_repo: SavingsSchedulerRepo,
) -> dict:
    await scheduler_repo.delete(asset_id)
    return await biz.delete_asset(asset_id, user_id, asset_repo)


# ── MCP tool registration ────────────────────────────────────────────────────

def register_savings_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def create_savings_deposit(
        name: str,
        amount: float,
        interest_rate: float,
        compound_frequency: str,
        start_date: str,
        maturity_date: str,
        category: str,
    ) -> dict:
        """Create a new savings deposit with compound interest.

        Args:
            name: Name of the savings (e.g. 'Bank Savings', 'Term Deposit')
            amount: Principal amount deposited
            interest_rate: Annual interest rate (e.g. 5.0 for 5%)
            compound_frequency: How often interest compounds: 'monthly', 'quarterly', or 'yearly'
            start_date: Start date in YYYY-MM-DD format
            maturity_date: End date in YYYY-MM-DD format
            category: Category (e.g. 'Savings')
        """
        db = await get_db()
        return await _create_savings_with_scheduler(
            get_user_id(), name, amount, interest_rate, compound_frequency,
            start_date, maturity_date, category,
            AssetRepository(db), SavingsSchedulerRepo(db),
        )

    @mcp.tool()
    async def list_savings(active_only: bool = True) -> list[dict]:
        """List all savings deposits with interest tracking."""
        db = await get_db()
        return await biz.list_savings(get_user_id(), AssetRepository(db), active_only)

    @mcp.tool()
    async def close_savings_early(asset_id: str) -> dict:
        """Close a savings deposit before its maturity date. Stops interest and deactivates."""
        db = await get_db()
        return await _close_savings_with_scheduler(
            asset_id, get_user_id(),
            AssetRepository(db), SavingsSchedulerRepo(db),
        )

    @mcp.tool()
    async def process_savings_interest(asset_id: str) -> dict:
        """Process compound interest for a savings deposit.
        Called automatically by the scheduler. Do not call manually.
        """
        db = await get_db()
        return await biz.process_savings_interest(
            asset_id, get_user_id(), AssetRepository(db),
        )
```

**Step 6: Run tests**

Run: `cd packages/mcp-server && pytest tests/test_tools/test_savings_lifecycle.py -v`

Expected: All PASS.

**Step 7: Commit**

```bash
git add packages/mcp-server/src/flux_mcp/db/savings_scheduler_repo.py \
       packages/mcp-server/src/flux_mcp/tools/savings_tools.py \
       packages/mcp-server/tests/test_tools/test_savings_lifecycle.py \
       packages/agent-bot/migrations/006_add_asset_id.sql
git commit -m "feat: add SavingsSchedulerRepo and MCP savings tools with scheduler wiring"
```

---

## Task 7: Register Savings Tools in MCP Server

**Files:**
- Modify: `packages/mcp-server/src/flux_mcp/server.py`

**Step 1: Find where tools are registered**

Look at `packages/mcp-server/src/flux_mcp/server.py` for the `register_financial_tools()` call. Add `register_savings_tools()` next to it.

**Step 2: Add registration**

Add import:
```python
from flux_mcp.tools.savings_tools import register_savings_tools
```

Add call next to existing tool registrations:
```python
register_savings_tools(mcp, get_db, get_user_id)
```

**Step 3: Run the full MCP server test suite**

Run: `cd packages/mcp-server && pytest tests/ -v`

Expected: All PASS.

**Step 4: Commit**

```bash
git add packages/mcp-server/src/flux_mcp/server.py
git commit -m "feat: register savings tools in MCP server"
```

---

## Task 8: Integration Tests — SavingsSchedulerRepo Against Real DB

**Files:**
- Create: `packages/mcp-server/tests/test_db/test_savings_scheduler_repo.py`

**Step 1: Write integration tests**

Create `packages/mcp-server/tests/test_db/test_savings_scheduler_repo.py`:

```python
"""Integration tests for SavingsSchedulerRepo against a real DB."""
from datetime import datetime, timezone
from uuid import UUID
import pytest

from flux_core.migrations.migrate import migrate as run_core_migrations
from flux_bot.db.migrate import run_migrations as run_bot_migrations
from flux_core.db.connection import Database
from flux_mcp.db.savings_scheduler_repo import SavingsSchedulerRepo


ASSET_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_ID = "tg:999"


@pytest.fixture
async def db(pg_url):
    await run_core_migrations(pg_url)
    await run_bot_migrations(pg_url)
    database = Database(pg_url)
    await database.connect()
    await database.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) "
        "ON CONFLICT DO NOTHING",
        USER_ID, "Test", "tg",
    )
    yield database
    await database.disconnect()


@pytest.fixture
def repo(db):
    return SavingsSchedulerRepo(db)


async def test_create_scheduler(repo, db):
    next_run = datetime(2027, 3, 1, tzinfo=timezone.utc)
    task_id = await repo.create(
        user_id=USER_ID,
        asset_id=str(ASSET_UUID),
        prompt="Process savings interest for Bank Savings (id: bbbbbbbb-...)",
        cron="0 0 1 3 *",
        next_run_at=next_run,
    )
    assert task_id is not None

    rows = await db.fetch(
        "SELECT * FROM bot_scheduled_tasks WHERE id = $1", task_id,
    )
    assert len(rows) == 1
    row = dict(rows[0])
    assert row["asset_id"] == ASSET_UUID
    assert row["schedule_type"] == "cron"
    assert row["schedule_value"] == "0 0 1 3 *"
    assert row["status"] == "active"


async def test_pause_and_resume(repo, db):
    next_run = datetime(2027, 3, 1, tzinfo=timezone.utc)
    await repo.create(USER_ID, str(ASSET_UUID), "prompt", "0 0 1 3 *", next_run)

    await repo.pause(str(ASSET_UUID))
    rows = await db.fetch(
        "SELECT status FROM bot_scheduled_tasks WHERE asset_id = $1", ASSET_UUID,
    )
    assert rows[0]["status"] == "paused"

    new_next_run = datetime(2028, 3, 1, tzinfo=timezone.utc)
    await repo.resume(str(ASSET_UUID), new_next_run)
    rows = await db.fetch(
        "SELECT status, next_run_at FROM bot_scheduled_tasks WHERE asset_id = $1", ASSET_UUID,
    )
    assert rows[0]["status"] == "active"


async def test_delete(repo, db):
    next_run = datetime(2027, 3, 1, tzinfo=timezone.utc)
    await repo.create(USER_ID, str(ASSET_UUID), "prompt", "0 0 1 3 *", next_run)

    await repo.delete(str(ASSET_UUID))
    rows = await db.fetch(
        "SELECT id FROM bot_scheduled_tasks WHERE asset_id = $1", ASSET_UUID,
    )
    assert len(rows) == 0
```

**Step 2: Run tests**

Run: `cd packages/mcp-server && pytest tests/test_db/test_savings_scheduler_repo.py -v`

Expected: All PASS.

**Step 3: Commit**

```bash
git add packages/mcp-server/tests/test_db/test_savings_scheduler_repo.py
git commit -m "test: add integration tests for SavingsSchedulerRepo"
```

---

## Task 9: Update delete_asset to Also Delete Scheduler Tasks

**Files:**
- Modify: `packages/mcp-server/src/flux_mcp/tools/financial_tools.py`
- Test: Update existing tests or add new ones

**Step 1: Write failing test**

In `packages/mcp-server/tests/test_tools/test_savings_lifecycle.py`, add:

```python
async def test_delete_asset_deletes_savings_scheduler():
    from flux_mcp.tools.savings_tools import _delete_savings_with_scheduler

    asset_repo = AsyncMock()
    asset_repo.delete.return_value = True
    scheduler_repo = AsyncMock()

    result = await _delete_savings_with_scheduler(
        asset_id=str(ASSET_UUID),
        user_id=USER_ID,
        asset_repo=asset_repo,
        scheduler_repo=scheduler_repo,
    )

    assert result["success"] is True
    scheduler_repo.delete.assert_called_once_with(str(ASSET_UUID))
```

**Step 2: Run test — should already pass** since `_delete_savings_with_scheduler` was implemented in Task 6.

Run: `cd packages/mcp-server && pytest tests/test_tools/test_savings_lifecycle.py::test_delete_asset_deletes_savings_scheduler -v`

Expected: PASS.

**Step 3: Commit**

```bash
git add packages/mcp-server/tests/test_tools/test_savings_lifecycle.py
git commit -m "test: add test for delete_asset with scheduler cleanup"
```

---

## Task 10: Full Test Suite Verification

**Step 1: Run all core tests**

Run: `cd packages/core && pytest tests/ -v`

Expected: All PASS.

**Step 2: Run all MCP server tests**

Run: `cd packages/mcp-server && pytest tests/ -v`

Expected: All PASS.

**Step 3: Run ruff linting**

Run: `cd packages/core && ruff check src/ tests/ && cd ../mcp-server && ruff check src/ tests/`

Expected: No errors.

**Step 4: Commit any lint fixes if needed**

```bash
git add -A && git commit -m "fix: address lint issues"
```

---

## Summary

| Task | Description | Commit message |
|------|-------------|----------------|
| 1 | Migration: savings columns | `feat: add savings columns to assets table (migration 005)` |
| 2 | Models: AssetType, AssetFrequency, new fields | `feat: add AssetType enum and savings fields to asset models` |
| 3 | Repository: get(), update_amount(), deactivate(), asset_type filter | `feat: update AssetRepository with savings columns` |
| 4 | Core tools: create_savings_deposit, process_savings_interest, list_savings, close_savings_early | `feat: add savings deposit business logic` |
| 5 | Refactor: _asset_to_dict helper for unified output | `refactor: unify asset dict output with _asset_to_dict helper` |
| 6 | SavingsSchedulerRepo + MCP tools wrapper + bot migration | `feat: add SavingsSchedulerRepo and MCP savings tools` |
| 7 | Register in MCP server | `feat: register savings tools in MCP server` |
| 8 | Integration tests for scheduler repo | `test: add integration tests for SavingsSchedulerRepo` |
| 9 | Delete asset cleans up scheduler | `test: add test for delete_asset with scheduler cleanup` |
| 10 | Full test suite verification | Final check |

## Follow-up (out of scope)

- Wire up scheduler automation for regular income assets (`asset_type='income'`)
