import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from flux_bot.runner.deepagent import DeepAgentRunner
from flux_bot.db.llm_config import UserLlmConfig
from flux_core.models.user_profile import UserProfile


def _profile():
    return UserProfile(
        user_id="tg:1",
        username="alice",
        currency="USD",
        timezone="UTC",
        locale="en",
        channel="telegram",
        platform_id="1",
    )


async def test_runner_returns_agent_result(tmp_path, monkeypatch, core_db):
    monkeypatch.setenv("FLUX_SECRET_KEY", "x" * 32)
    profile = _profile()
    cfg = UserLlmConfig("tg:1", "anthropic", "claude-sonnet-4-6", None, "sk-ant-api-KEY")

    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="hello user")]})

    with patch("flux_bot.agent.factory.init_chat_model"), patch(
        "flux_bot.agent.factory.create_deep_agent", return_value=fake_graph
    ):
        runner = DeepAgentRunner(
            db=core_db,
            flux_db_path=str(tmp_path / "flux.db"),
            timeout=30,
        )
        result = await runner.run(
            prompt="hi",
            user_id="tg:1",
            thread_id="tg:1:telegram:abc",
            profile=profile,
            llm_config=cfg,
        )
        assert result.text == "hello user"
        assert result.error is None


async def test_runner_returns_error_on_timeout(tmp_path, monkeypatch, core_db):
    monkeypatch.setenv("FLUX_SECRET_KEY", "x" * 32)
    profile = _profile()
    cfg = UserLlmConfig("tg:1", "anthropic", "claude-sonnet-4-6", None, "sk-ant-api-KEY")

    fake_graph = MagicMock()

    async def slow_invoke(*_, **__):
        await asyncio.sleep(10)
        return {}

    fake_graph.ainvoke = slow_invoke

    with patch("flux_bot.agent.factory.init_chat_model"), patch(
        "flux_bot.agent.factory.create_deep_agent", return_value=fake_graph
    ):
        runner = DeepAgentRunner(
            db=core_db,
            flux_db_path=str(tmp_path / "flux.db"),
            timeout=0,  # instant timeout
        )
        result = await runner.run(
            prompt="hi",
            user_id="tg:1",
            thread_id="t1",
            profile=profile,
            llm_config=cfg,
        )
        assert result.error is not None
        assert result.text is None
