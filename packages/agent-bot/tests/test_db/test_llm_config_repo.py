"""Tests for UserLlmConfigRepository (dual-purpose: persist + encrypt)."""
import pytest

from flux_bot.db.llm_config import UserLlmConfig, UserLlmConfigRepository
from flux_core.sqlite.database import Database
from flux_core.sqlite.migrations.migrate import migrate


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setenv("FLUX_SECRET_KEY", "test-secret-0123456789abcdef")
    path = tmp_path / "flux.db"
    db = Database(str(path))
    db.connect()
    migrate(db)
    try:
        yield db
    finally:
        db.disconnect()


async def test_upsert_then_get_decrypts(db):
    repo = UserLlmConfigRepository(db)
    await repo.upsert(
        UserLlmConfig(
            user_id="tg:1",
            provider="anthropic",
            model="claude-sonnet-4-6",
            base_url=None,
            api_key="sk-ant-api-SECRET",
        )
    )
    got = await repo.get("tg:1")
    assert got is not None
    assert got.provider == "anthropic"
    assert got.api_key == "sk-ant-api-SECRET"  # decrypted on read


async def test_get_missing_returns_none(db):
    repo = UserLlmConfigRepository(db)
    assert await repo.get("tg:missing") is None


async def test_upsert_updates_existing(db):
    repo = UserLlmConfigRepository(db)
    await repo.upsert(
        UserLlmConfig("tg:1", "anthropic", "claude-sonnet-4-6", None, "sk-ant-api-A")
    )
    await repo.upsert(
        UserLlmConfig("tg:1", "openai", "gpt-5.4", None, "sk-openai-B")
    )
    got = await repo.get("tg:1")
    assert got is not None
    assert got.provider == "openai"
    assert got.api_key == "sk-openai-B"


async def test_delete(db):
    repo = UserLlmConfigRepository(db)
    await repo.upsert(
        UserLlmConfig("tg:1", "anthropic", "claude-sonnet-4-6", None, "sk-ant-api-A")
    )
    await repo.delete("tg:1")
    assert await repo.get("tg:1") is None


async def test_repr_masks_api_key(db, monkeypatch):
    # FLUX_SECRET_KEY is only needed for enc/dec, not for repr.
    cfg = UserLlmConfig(
        "tg:1", "anthropic", "claude-sonnet-4-6", None, "sk-ant-api-SECRET"
    )
    text = repr(cfg)
    assert "sk-ant-api-SECRET" not in text
    assert "CRET" in text  # last 4 chars visible
