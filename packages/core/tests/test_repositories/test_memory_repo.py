"""Tests for SqliteMemoryRepository."""
from uuid import UUID

import pytest
from flux_core.models.memory import MemoryCreate, MemoryOut, MemoryType
from flux_core.sqlite.memory_repo import SqliteMemoryRepository


@pytest.fixture
def repo(conn):
    return SqliteMemoryRepository(conn)


def _make_memory(user_id: str, **overrides) -> MemoryCreate:
    defaults = dict(
        user_id=user_id,
        memory_type=MemoryType.fact,
        content="User prefers VND currency",
    )
    defaults.update(overrides)
    return MemoryCreate(**defaults)


class TestCreate:
    def test_creates_memory(self, repo, user_id):
        result = repo.create(_make_memory(user_id))
        assert isinstance(result, MemoryOut)
        assert isinstance(result.id, UUID)
        assert result.memory_type == MemoryType.fact
        assert result.content == "User prefers VND currency"
        assert result.created_at is not None

    def test_creates_different_types(self, repo, user_id):
        for mt in MemoryType:
            result = repo.create(_make_memory(user_id, memory_type=mt, content=mt.value))
            assert result.memory_type == mt


class TestGetByIds:
    def test_returns_matching(self, repo, user_id):
        m1 = repo.create(_make_memory(user_id, content="A"))
        m2 = repo.create(_make_memory(user_id, content="B"))
        results = repo.get_by_ids([m1.id, m2.id])
        assert len(results) == 2

    def test_empty_list(self, repo):
        assert repo.get_by_ids([]) == []


class TestListByUser:
    def test_lists_all(self, repo, user_id):
        repo.create(_make_memory(user_id, content="A"))
        repo.create(_make_memory(user_id, content="B"))
        results = repo.list_by_user(user_id)
        assert len(results) == 2

    def test_filter_by_type(self, repo, user_id):
        repo.create(_make_memory(user_id, memory_type=MemoryType.fact))
        repo.create(_make_memory(user_id, memory_type=MemoryType.preference))
        results = repo.list_by_user(user_id, memory_type="fact")
        assert len(results) == 1
        assert results[0].memory_type == MemoryType.fact

    def test_limit(self, repo, user_id):
        for i in range(10):
            repo.create(_make_memory(user_id, content=f"Memory {i}"))
        results = repo.list_by_user(user_id, limit=3)
        assert len(results) == 3

    def test_order_by_created_at_desc(self, repo, user_id):
        repo.create(_make_memory(user_id, content="First"))
        repo.create(_make_memory(user_id, content="Second"))
        results = repo.list_by_user(user_id)
        # most recent first
        assert results[0].content == "Second"

    def test_empty(self, repo, user_id):
        assert repo.list_by_user(user_id) == []
