import pytest
from decimal import Decimal

from flux_core.db.connection import Database
from flux_core.db.budget_repo import BudgetRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.budget import BudgetSet


@pytest.fixture
async def db(pg_url):
    await migrate(pg_url)
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def user_id(db):
    uid = "test:budget_user"
    await db.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        uid, "Budget User", "test",
    )
    return uid


@pytest.fixture
def repo(db):
    return BudgetRepository(db)


async def test_set_budget(repo, user_id):
    budget = BudgetSet(user_id=user_id, category="Food", monthly_limit=Decimal("500"))
    result = await repo.set(budget)
    assert result.monthly_limit == Decimal("500")


async def test_upsert_budget(repo, user_id):
    budget = BudgetSet(user_id=user_id, category="Food", monthly_limit=Decimal("600"))
    result = await repo.set(budget)
    assert result.monthly_limit == Decimal("600")


async def test_list_budgets(repo, user_id):
    results = await repo.list_by_user(user_id)
    assert len(results) >= 1


async def test_remove_budget(repo, user_id):
    removed = await repo.remove(user_id, "Food")
    assert removed is True
