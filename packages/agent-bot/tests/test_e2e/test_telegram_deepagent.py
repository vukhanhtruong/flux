"""E2E test: Telegram inbound message → DeepAgentRunner → channel reply.

Uses a real (in-memory temp) SQLite database with full migrations applied.
DeepAgentRunner.run is patched so no LLM or LangGraph network calls happen.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from flux_bot.db.llm_config import UserLlmConfig, UserLlmConfigRepository
from flux_bot.db.messages import MessageRepository
from flux_bot.db.profile import ProfileRepository
from flux_bot.db.sessions import SessionRepository
from flux_bot.orchestrator.handler import make_handle_message
from flux_bot.runner.deepagent import DeepAgentRunner
from flux_bot.runner.result import AgentResult


async def _seed_user(db, user_id: str, platform_id: str) -> None:
    """Insert a minimal user row directly so we can set the user_id we want."""
    db.execute(
        """
        INSERT INTO users (id, username, platform, platform_id, currency, timezone)
        VALUES (?, ?, 'telegram', ?, 'VND', 'Asia/Ho_Chi_Minh')
        """,
        (user_id, "testuser", platform_id),
    )


async def test_telegram_deepagent_happy_path(core_db, tmp_path, monkeypatch):
    """Full pipeline: message in DB → handler calls DeepAgentRunner → reply sent."""
    monkeypatch.setenv("FLUX_SECRET_KEY", "x" * 32)

    user_id = "tg:1"
    platform_id = "1"

    # Seed user profile
    await _seed_user(core_db, user_id, platform_id)

    # Seed LLM config
    llm_config_repo = UserLlmConfigRepository(core_db)
    await llm_config_repo.upsert(
        UserLlmConfig(
            user_id=user_id,
            provider="anthropic",
            model="claude-sonnet-4-6",
            base_url=None,
            api_key="sk-ant-test-key-12345",
        )
    )

    msg = {
        "id": 1,
        "user_id": user_id,
        "channel": "telegram",
        "platform_id": platform_id,
        "text": "hello agent",
        "image_path": None,
    }

    mock_channel = MagicMock()
    mock_channel.send_message = AsyncMock()

    msg_repo = MessageRepository(core_db)
    session_repo = SessionRepository(core_db)
    profile_repo = ProfileRepository(core_db)

    runner = DeepAgentRunner(db=core_db, flux_db_path=str(tmp_path / "flux.db"), timeout=30)

    with patch.object(
        runner, "run", new=AsyncMock(return_value=AgentResult(text="hello", thread_id="t1"))
    ):
        handler = make_handle_message(
            runner=runner,
            msg_repo=msg_repo,
            session_repo=session_repo,
            profile_repo=profile_repo,
            llm_config_repo=llm_config_repo,
            channels={"telegram": mock_channel},
        )
        await handler(msg)

    mock_channel.send_message.assert_called_once_with(platform_id, "hello")


async def test_telegram_deepagent_no_llm_config_sends_setup_prompt(core_db, tmp_path, monkeypatch):
    """When LLM config is missing, user receives setup prompt, message marked processed."""
    monkeypatch.setenv("FLUX_SECRET_KEY", "x" * 32)

    user_id = "tg:2"
    platform_id = "2"

    await _seed_user(core_db, user_id, platform_id)

    llm_config_repo = UserLlmConfigRepository(core_db)  # no config seeded

    msg = {
        "id": 2,
        "user_id": user_id,
        "channel": "telegram",
        "platform_id": platform_id,
        "text": "show me my balance",
        "image_path": None,
    }

    mock_channel = MagicMock()
    mock_channel.send_message = AsyncMock()

    msg_repo = MagicMock()
    msg_repo.mark_processed = AsyncMock()
    msg_repo.mark_failed = AsyncMock()

    session_repo = SessionRepository(core_db)
    profile_repo = ProfileRepository(core_db)

    runner = DeepAgentRunner(db=core_db, flux_db_path=str(tmp_path / "flux.db"), timeout=30)

    handler = make_handle_message(
        runner=runner,
        msg_repo=msg_repo,
        session_repo=session_repo,
        profile_repo=profile_repo,
        llm_config_repo=llm_config_repo,
        channels={"telegram": mock_channel},
    )
    await handler(msg)

    mock_channel.send_message.assert_called_once()
    sent_text = mock_channel.send_message.call_args.args[1]
    assert "settings" in sent_text.lower() or "llm" in sent_text.lower()
    msg_repo.mark_processed.assert_awaited_once_with(2)
    msg_repo.mark_failed.assert_not_awaited()


async def test_telegram_deepagent_thread_id_persisted(core_db, tmp_path, monkeypatch):
    """Second message for same user reuses the same thread_id from session store."""
    monkeypatch.setenv("FLUX_SECRET_KEY", "x" * 32)

    user_id = "tg:3"
    platform_id = "3"

    await _seed_user(core_db, user_id, platform_id)

    llm_config_repo = UserLlmConfigRepository(core_db)
    await llm_config_repo.upsert(
        UserLlmConfig(
            user_id=user_id,
            provider="anthropic",
            model="claude-sonnet-4-6",
            base_url=None,
            api_key="sk-ant-test-key-99999",
        )
    )

    session_repo = SessionRepository(core_db)
    profile_repo = ProfileRepository(core_db)

    mock_channel = MagicMock()
    mock_channel.send_message = AsyncMock()

    call_thread_ids = []

    async def capture_run(*, prompt, user_id, thread_id, image_path, profile, llm_config):
        call_thread_ids.append(thread_id)
        return AgentResult(text="reply", thread_id=thread_id)

    runner = DeepAgentRunner(db=core_db, flux_db_path=str(tmp_path / "flux.db"), timeout=30)

    msg_repo = MagicMock()
    msg_repo.mark_processed = AsyncMock()
    msg_repo.mark_failed = AsyncMock()

    with patch.object(runner, "run", side_effect=capture_run):
        handler = make_handle_message(
            runner=runner,
            msg_repo=msg_repo,
            session_repo=session_repo,
            profile_repo=profile_repo,
            llm_config_repo=llm_config_repo,
            channels={"telegram": mock_channel},
        )
        msg1 = {"id": 3, "user_id": user_id, "channel": "telegram",
                "platform_id": platform_id, "text": "msg 1", "image_path": None}
        msg2 = {"id": 4, "user_id": user_id, "channel": "telegram",
                "platform_id": platform_id, "text": "msg 2", "image_path": None}
        await handler(msg1)
        await handler(msg2)

    # Both messages must use the same thread_id
    assert len(call_thread_ids) == 2
    assert call_thread_ids[0] == call_thread_ids[1]
