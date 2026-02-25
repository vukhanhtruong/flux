import pytest
from datetime import date
from decimal import Decimal

from flux_core.db.connection import Database
from flux_core.db.goal_repo import GoalRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.goal import GoalCreate


@pytest.fixture
async def db(pg_url):
    await migrate(pg_url)
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def user_id(db):
    uid = "test:goal_user"
    await db.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        uid, "Goal User", "test",
    )
    return uid


@pytest.fixture
def repo(db):
    return GoalRepository(db)


async def test_create_goal(repo, user_id):
    goal = GoalCreate(
        user_id=user_id,
        name="Vacation Fund",
        target_amount=Decimal("5000"),
        deadline=date(2026, 12, 31),
    )
    result = await repo.create(goal)
    assert result.name == "Vacation Fund"
    assert result.target_amount == Decimal("5000")
    assert result.current_amount == Decimal("0")


async def test_deposit_to_goal(repo, user_id):
    goal = GoalCreate(
        user_id=user_id,
        name="Emergency Fund",
        target_amount=Decimal("10000"),
    )
    created = await repo.create(goal)
    updated = await repo.deposit(created.id, user_id, Decimal("500"))
    assert updated.current_amount == Decimal("500")


async def test_list_goals(repo, user_id):
    results = await repo.list_by_user(user_id)
    assert len(results) >= 2
