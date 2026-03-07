"""Tests for memory use cases."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.models.memory import MemoryOut, MemoryType
from flux_core.use_cases.memory import ListMemories, Recall, Remember

USER_ID = "tg:12345"
FAKE_ID = uuid4()
FAKE_NOW = datetime(2026, 3, 7, 12, 0, 0)
FAKE_EMBEDDING = [0.1] * 384


def _make_memory(**overrides) -> MemoryOut:
    defaults = {
        "id": FAKE_ID,
        "user_id": USER_ID,
        "memory_type": MemoryType.fact,
        "content": "User prefers Vietnamese dong for currency",
        "created_at": FAKE_NOW,
    }
    defaults.update(overrides)
    return MemoryOut(**defaults)


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    uow.add_vector = MagicMock()
    uow.add_event = MagicMock()
    return uow


def _mock_embedding_svc():
    svc = MagicMock()
    svc.embed.return_value = FAKE_EMBEDDING
    return svc


# ── Remember ────────────────────────────────────────────────────────────


@patch("flux_core.use_cases.memory.remember.SqliteMemoryRepository")
async def test_remember(mock_repo_cls):
    uow = _mock_uow()
    svc = _mock_embedding_svc()
    expected = _make_memory()
    mock_repo_cls.return_value.create.return_value = expected

    uc = Remember(uow, svc)
    result = await uc.execute(USER_ID, MemoryType.fact, "User prefers VND")

    assert result.id == FAKE_ID
    svc.embed.assert_called_once_with("User prefers VND")
    uow.add_vector.assert_called_once()
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


# ── Recall ──────────────────────────────────────────────────────────────


async def test_recall():
    svc = _mock_embedding_svc()
    memory = _make_memory()
    repo = MagicMock()
    repo.get_by_ids.return_value = [memory]
    vector_store = MagicMock()
    vector_store.search.return_value = [str(FAKE_ID)]

    uc = Recall(repo, vector_store, svc)
    result = await uc.execute(USER_ID, "currency preference")

    assert len(result) == 1
    svc.embed.assert_called_once_with("currency preference")
    vector_store.search.assert_called_once()
    repo.get_by_ids.assert_called_once()


async def test_recall_no_results():
    svc = _mock_embedding_svc()
    repo = MagicMock()
    vector_store = MagicMock()
    vector_store.search.return_value = []

    uc = Recall(repo, vector_store, svc)
    result = await uc.execute(USER_ID, "nonexistent")

    assert result == []
    repo.get_by_ids.assert_not_called()


# ── ListMemories ────────────────────────────────────────────────────────


async def test_list_memories():
    memories = [_make_memory(), _make_memory(id=uuid4())]
    repo = MagicMock()
    repo.list_by_user.return_value = memories

    uc = ListMemories(repo)
    result = await uc.execute(USER_ID)

    assert len(result) == 2
    repo.list_by_user.assert_called_once_with(USER_ID, memory_type=None, limit=50)


async def test_list_memories_filtered():
    repo = MagicMock()
    repo.list_by_user.return_value = []

    uc = ListMemories(repo)
    await uc.execute(USER_ID, memory_type="fact", limit=10)

    repo.list_by_user.assert_called_once_with(USER_ID, memory_type="fact", limit=10)
