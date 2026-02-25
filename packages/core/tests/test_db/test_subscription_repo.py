import pytest
from datetime import date
from decimal import Decimal

from flux_core.db.connection import Database
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.subscription import SubscriptionCreate


@pytest.fixture
async def db(pg_url):
    await migrate(pg_url)
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def user_id(db):
    uid = "test:sub_user"
    await db.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        uid, "Sub User", "test",
    )
    return uid


@pytest.fixture
def repo(db):
    return SubscriptionRepository(db)


async def test_create_subscription(repo, user_id):
    sub = SubscriptionCreate(
        user_id=user_id,
        name="Netflix",
        amount=Decimal("15.99"),
        billing_cycle="monthly",
        next_date=date(2026, 3, 1),
        category="Entertainment",
    )
    result = await repo.create(sub)
    assert result.name == "Netflix"
    assert result.active is True


async def test_list_subscriptions(repo, user_id):
    results = await repo.list_by_user(user_id)
    assert len(results) >= 1
