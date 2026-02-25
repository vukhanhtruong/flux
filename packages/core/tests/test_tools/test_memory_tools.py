from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
import pytest

from flux_core.tools.memory_tools import (
    remember,
    recall,
    list_memories,
)
from flux_core.models.memory import MemoryOut, MemoryType


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.embed.return_value = [0.1] * 384
    return service


@pytest.mark.asyncio
async def test_remember(mock_repo, mock_embedding_service):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.create.return_value = MemoryOut(
        id=test_uuid,
        user_id="test_user",
        memory_type=MemoryType.preference,
        content="User prefers coffee over tea",
        created_at=datetime.now()
    )

    result = await remember(
        user_id="test_user",
        memory_type="preference",
        content="User prefers coffee over tea",
        repo=mock_repo,
        embedding_service=mock_embedding_service
    )

    assert result["id"] == str(test_uuid)
    assert result["memory_type"] == "preference"
    assert result["content"] == "User prefers coffee over tea"
    mock_repo.create.assert_called_once()
    mock_embedding_service.embed.assert_called_once_with("User prefers coffee over tea")


@pytest.mark.asyncio
async def test_recall(mock_repo, mock_embedding_service):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.search_by_embedding.return_value = [
        MemoryOut(
            id=test_uuid,
            user_id="test_user",
            memory_type=MemoryType.fact,
            content="User's monthly rent is $1200",
            created_at=datetime.now()
        )
    ]

    result = await recall(
        user_id="test_user",
        query="rent amount",
        limit=5,
        repo=mock_repo,
        embedding_service=mock_embedding_service
    )

    assert len(result) == 1
    assert result[0]["content"] == "User's monthly rent is $1200"
    mock_embedding_service.embed.assert_called_once_with("rent amount")
    mock_repo.search_by_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_list_memories(mock_repo):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        MemoryOut(
            id=test_uuid,
            user_id="test_user",
            memory_type=MemoryType.preference,
            content="User prefers coffee over tea",
            created_at=datetime.now()
        )
    ]

    result = await list_memories(
        user_id="test_user",
        memory_type="preference",
        repo=mock_repo
    )

    assert len(result) == 1
    assert result[0]["memory_type"] == "preference"
    mock_repo.list_by_user.assert_called_once_with("test_user", "preference")


@pytest.mark.asyncio
async def test_list_all_memories(mock_repo):
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mock_repo.list_by_user.return_value = [
        MemoryOut(
            id=test_uuid,
            user_id="test_user",
            memory_type=MemoryType.fact,
            content="Some fact",
            created_at=datetime.now()
        )
    ]

    result = await list_memories(
        user_id="test_user",
        repo=mock_repo
    )

    assert len(result) == 1
    mock_repo.list_by_user.assert_called_once_with("test_user", None)
