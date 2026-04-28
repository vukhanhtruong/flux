"""Tests for SqliteLlmConfigRepository."""
import pytest

from flux_core.sqlite.database import Database
from flux_core.sqlite.bot.llm_config_repo import SqliteLlmConfigRepository, LlmConfig


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database = Database(str(db_path))
    database.connect()
    database.execute("""
        CREATE TABLE IF NOT EXISTS bot_user_llm_config (
            user_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            base_url TEXT,
            api_key_encrypted TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    return database


def test_get_returns_none_when_not_exists(db):
    repo = SqliteLlmConfigRepository(db, encryption_key="test-secret-key")
    result = repo.get("tg:12345")
    assert result is None


def test_upsert_and_get(db):
    repo = SqliteLlmConfigRepository(db, encryption_key="test-secret-key")
    cfg = LlmConfig(
        user_id="tg:12345",
        provider="anthropic",
        model="claude-sonnet-4-6",
        base_url=None,
        api_key="sk-ant-test-key",
    )
    repo.upsert(cfg)

    result = repo.get("tg:12345")
    assert result is not None
    assert result.user_id == "tg:12345"
    assert result.provider == "anthropic"
    assert result.model == "claude-sonnet-4-6"
    assert result.base_url is None
    assert result.api_key == "sk-ant-test-key"


def test_upsert_updates_existing(db):
    repo = SqliteLlmConfigRepository(db, encryption_key="test-secret-key")

    cfg1 = LlmConfig(
        user_id="tg:12345",
        provider="anthropic",
        model="claude-sonnet-4-6",
        base_url=None,
        api_key="sk-ant-key-1",
    )
    repo.upsert(cfg1)

    cfg2 = LlmConfig(
        user_id="tg:12345",
        provider="openai",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key="sk-openai-key",
    )
    repo.upsert(cfg2)

    result = repo.get("tg:12345")
    assert result.provider == "openai"
    assert result.model == "gpt-4o"
    assert result.api_key == "sk-openai-key"


def test_delete(db):
    repo = SqliteLlmConfigRepository(db, encryption_key="test-secret-key")
    cfg = LlmConfig(
        user_id="tg:12345",
        provider="anthropic",
        model="claude-sonnet-4-6",
        base_url=None,
        api_key="sk-ant-test-key",
    )
    repo.upsert(cfg)

    repo.delete("tg:12345")
    result = repo.get("tg:12345")
    assert result is None


def test_mask_api_key():
    from flux_core.sqlite.bot.llm_config_repo import mask_api_key

    assert mask_api_key("sk-ant-api03-verylongkey") == "sk-a...gkey"
    assert mask_api_key("short") == "..."
    assert mask_api_key("12345678") == "1234...5678"
