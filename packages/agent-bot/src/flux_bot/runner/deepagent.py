"""DeepAgentRunner — LangGraph-based agent runner using the deepagents SDK."""

import asyncio
import logging
from pathlib import Path

from flux_core.sqlite.database import Database
from flux_core.models.user_profile import UserProfile
from flux_bot.agent.factory import build_agent
from flux_bot.agent.checkpointer import build_checkpointer
from flux_bot.agent.prompt import prepend_datetime
from flux_bot.db.llm_config import UserLlmConfig
from flux_bot.runner.errors import map_runner_error
from flux_bot.runner.result import AgentResult
from flux_bot.tools import build_tools

logger = logging.getLogger(__name__)


class DeepAgentRunner:
    def __init__(self, *, db: Database, flux_db_path: str, timeout: int = 300):
        self.db = db
        self.flux_db_path = flux_db_path
        self.timeout = timeout

    async def run(
        self,
        *,
        prompt: str,
        user_id: str,
        thread_id: str,
        profile: UserProfile,
        llm_config: UserLlmConfig,
        image_path: str | None = None,
    ) -> AgentResult:
        full_prompt = prepend_datetime(prompt, profile)
        if image_path:
            full_prompt = f"{full_prompt}\n\n[Image: {image_path}]"

        tools = build_tools(user_id=user_id, db=self.db)

        p = Path(self.flux_db_path)
        checkpoint_db_path = str(p.parent / (p.stem + "_checkpoints" + p.suffix))

        try:
            async with asyncio.timeout(self.timeout):
                async with build_checkpointer(checkpoint_db_path) as ckpt:
                    agent = build_agent(
                        llm_config=llm_config,
                        profile=profile,
                        tools=tools,
                        checkpointer=ckpt,
                    )
                    result = await agent.ainvoke(
                        {"messages": [{"role": "user", "content": full_prompt}]},
                        config={"configurable": {"thread_id": thread_id}},
                    )
            text = result["messages"][-1].content if result.get("messages") else None
            return AgentResult(text=text, thread_id=thread_id)
        except asyncio.TimeoutError:
            logger.error("DeepAgent timed out for user=%s", user_id)
            return AgentResult(text=None, thread_id=thread_id, error=map_runner_error("timeout"))
        except Exception as e:
            logger.exception("DeepAgent error for user=%s", user_id)
            return AgentResult(text=None, thread_id=thread_id, error=map_runner_error(str(e)))
