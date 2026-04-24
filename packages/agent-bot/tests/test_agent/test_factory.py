import pytest
from unittest.mock import MagicMock, patch

from flux_core.models.user_profile import UserProfile
from flux_bot.db.llm_config import UserLlmConfig
from flux_bot.agent.factory import build_agent


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


def test_build_agent_passes_correct_kwargs(monkeypatch):
    monkeypatch.setenv("FLUX_SECRET_KEY", "test-secret-0123456789abcdef")

    profile = _profile()
    cfg = UserLlmConfig("tg:1", "anthropic", "claude-sonnet-4-6", None, "sk-ant-api-KEY")

    with patch("flux_bot.agent.factory.create_deep_agent") as cda, patch(
        "flux_bot.agent.factory.init_chat_model"
    ) as icm:
        icm.return_value = MagicMock(name="model")
        cda.return_value = MagicMock(name="graph")

        tools = []
        ckpt = MagicMock(name="checkpointer")
        agent = build_agent(llm_config=cfg, profile=profile, tools=tools, checkpointer=ckpt)

        icm.assert_called_once()
        kwargs = icm.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["model_provider"] == "anthropic"
        assert kwargs["api_key"] == "sk-ant-api-KEY"

        cda.assert_called_once()
        assert cda.call_args.kwargs["tools"] is tools
        assert cda.call_args.kwargs["checkpointer"] is ckpt
        assert "alice" in cda.call_args.kwargs["system_prompt"]
        assert agent is cda.return_value


@pytest.mark.parametrize(
    "stored_provider, expected_provider",
    [
        ("anthropic", "anthropic"),
        ("openai", "openai"),
        ("groq", "groq"),
        ("openrouter", "openai"),
        ("custom", "openai"),
    ],
)
def test_build_agent_normalises_provider(stored_provider, expected_provider):
    """openrouter and custom are OpenAI-compatible — must be passed as 'openai'."""
    cfg = UserLlmConfig("tg:1", stored_provider, "some-model", "https://base.url", "key")

    with patch("flux_bot.agent.factory.create_deep_agent") as cda, patch(
        "flux_bot.agent.factory.init_chat_model"
    ) as icm:
        icm.return_value = MagicMock()
        cda.return_value = MagicMock()
        build_agent(llm_config=cfg, profile=_profile(), tools=[], checkpointer=MagicMock())
        assert icm.call_args.kwargs["model_provider"] == expected_provider
