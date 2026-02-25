import pytest
from datetime import date
from decimal import Decimal

from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.migrations.migrate import migrate
from flux_core.models.transaction import TransactionCreate


@pytest.fixture
async def db(pg_url):
    await migrate(pg_url)
    database = Database(pg_url)
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture
async def user_id(db):
    """Create a test user and return their ID."""
    uid = "test:user1"
    await db.execute(
        "INSERT INTO users (id, display_name, platform) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        uid, "Test User", "test",
    )
    return uid


@pytest.fixture
def repo(db):
    return TransactionRepository(db)


async def test_create_transaction(repo, user_id):
    txn = TransactionCreate(
        user_id=user_id,
        date=date(2026, 2, 13),
        amount=Decimal("15.50"),
        category="Food",
        description="Lunch at Chipotle",
        type="expense",
        tags=["work"],
    )
    result = await repo.create(txn)
    assert result.amount == Decimal("15.50")
    assert result.category == "Food"
    assert result.id is not None


async def test_get_by_id(repo, user_id):
    txn = TransactionCreate(
        user_id=user_id,
        date=date(2026, 2, 13),
        amount=Decimal("25.00"),
        category="Transport",
        description="Uber ride",
        type="expense",
    )
    created = await repo.create(txn)
    fetched = await repo.get_by_id(created.id, user_id)
    assert fetched is not None
    assert fetched.description == "Uber ride"


async def test_list_by_user(repo, user_id):
    results = await repo.list_by_user(user_id, limit=100)
    assert len(results) >= 2


async def test_delete(repo, user_id):
    txn = TransactionCreate(
        user_id=user_id,
        date=date.today(),
        amount=Decimal("5.00"),
        category="Other",
        description="To delete",
        type="expense",
    )
    created = await repo.create(txn)
    deleted = await repo.delete(created.id, user_id)
    assert deleted is True
    fetched = await repo.get_by_id(created.id, user_id)
    assert fetched is None


async def test_create_with_embedding(repo, user_id):
    """Embedding as list[float] must be stored without error."""
    embedding = [0.1] * 384  # 384-dim vector matching all-MiniLM-L6-v2
    txn = TransactionCreate(
        user_id=user_id,
        date=date.today(),
        amount=Decimal("50000.00"),
        category="Food",
        description="Lunch",
        type="expense",
    )
    result = await repo.create(txn, embedding)
    assert result.id is not None
    assert result.description == "Lunch"


async def test_search_by_embedding(repo, user_id):
    """search_by_embedding must return results after create_with_embedding."""
    embedding = [0.1] * 384
    txn = TransactionCreate(
        user_id=user_id,
        date=date.today(),
        amount=Decimal("20000.00"),
        category="Food",
        description="Breakfast",
        type="expense",
    )
    await repo.create(txn, embedding)
    results = await repo.search_by_embedding(user_id, embedding, limit=5)
    assert len(results) >= 1
    descriptions = [r.description for r in results]
    assert "Breakfast" in descriptions
