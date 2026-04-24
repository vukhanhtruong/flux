"""Build a deepagents CompiledGraph for a specific user."""

from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool
from deepagents import create_deep_agent

from flux_core.models.user_profile import UserProfile
from flux_bot.db.llm_config import UserLlmConfig
from flux_bot.agent.prompt import build_system_prompt

# Providers that are OpenAI-compatible but not recognized by init_chat_model
_OPENAI_COMPAT = {"openrouter", "custom"}


def build_agent(
    *,
    llm_config: UserLlmConfig,
    profile: UserProfile,
    tools: list[BaseTool],
    checkpointer,
):
    """Instantiate a deepagents CompiledStateGraph for one user request."""
    provider = "openai" if llm_config.provider in _OPENAI_COMPAT else llm_config.provider
    kwargs: dict = {
        "model": llm_config.model,
        "model_provider": provider,
        "api_key": llm_config.api_key,
    }
    if llm_config.base_url:
        kwargs["base_url"] = llm_config.base_url
    model = init_chat_model(**kwargs)

    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt(profile=profile),
        checkpointer=checkpointer,
    )
