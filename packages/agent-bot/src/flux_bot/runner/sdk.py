"""Claude Agent SDK runner (Python)."""

import asyncio
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, SystemMessage, query

if TYPE_CHECKING:
    from flux_core.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResult:
    text: str | None
    session_id: str | None
    error: str | None = None


class ClaudeRunner:
    def __init__(
        self,
        mcp_config_path: str,
        timeout: int = 300,
        model: str | None = None,
        system_prompt: str | None = None,
        max_turns: int = 10,
    ):
        self.mcp_config_path = mcp_config_path
        self.timeout = timeout
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.auth_token_env = "CLAUDE_AUTH_TOKEN"

    async def run(
        self,
        prompt: str,
        user_id: str,
        session_id: str | None = None,
        image_path: str | None = None,
        profile: "UserProfile | None" = None,
    ) -> ClaudeResult:
        """Run one Claude query via Python Agent SDK."""
        self._restore_claude_config_if_missing()
        self._setup_env()

        full_prompt = prompt
        if image_path:
            full_prompt = f"{prompt}\n\n[Image: {image_path}]"

        mcp_servers = self._build_mcp_servers(profile)
        system_prompt_text = self._build_system_prompt(profile) or self._load_system_prompt_text()
        stderr_lines: list[str] = []

        def _capture_stderr(line: str) -> None:
            # Keep only the latest lines to avoid unbounded memory on noisy stderr streams.
            if not line:
                return
            stderr_lines.append(line)
            if len(stderr_lines) > 50:
                del stderr_lines[:-50]

        options = ClaudeAgentOptions(
            resume=session_id,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt_text,
            permission_mode="bypassPermissions",
            max_turns=self.max_turns,
            model=self.model,
            stderr=_capture_stderr,
        )

        new_session_id = session_id
        result_text = None
        result_error = None

        logger.info(f"Running Claude SDK for user={user_id}")
        try:
            async with asyncio.timeout(self.timeout):
                async for message in query(prompt=full_prompt, options=options):
                    if isinstance(message, SystemMessage) and message.subtype == "init":
                        new_session_id = message.data.get("session_id", new_session_id)
                    elif isinstance(message, ResultMessage):
                        new_session_id = message.session_id
                        if message.is_error:
                            result_error = message.result or "SDK returned an error result"
                        else:
                            result_text = message.result
        except asyncio.TimeoutError:
            logger.error(f"Claude SDK timed out for user={user_id}")
            return ClaudeResult(text=None, session_id=session_id, error="Timeout")
        except Exception as e:
            logger.error(f"Claude SDK error for user={user_id}: {e}")
            return ClaudeResult(
                text=None,
                session_id=session_id,
                error=self._build_error_with_stderr(e, stderr_lines),
            )

        if result_error is not None:
            return ClaudeResult(text=None, session_id=new_session_id, error=result_error)
        return ClaudeResult(text=result_text, session_id=new_session_id)

    def _build_error_with_stderr(self, error: Exception, stderr_lines: list[str]) -> str:
        """Attach captured stderr details when SDK exception text only includes a placeholder."""
        message = str(error)
        if not stderr_lines:
            return message

        details = "\n".join(line.strip() for line in stderr_lines if line.strip()).strip()
        if not details:
            return message

        if "check stderr output for details" in message.lower():
            return f"{message}\nStderr details: {details}"
        return message

    def _build_mcp_servers(self, profile: "UserProfile | None") -> dict:
        """Build MCP servers dict from config file, injecting user_id into args."""
        base = json.loads(Path(self.mcp_config_path).read_text())
        servers: dict = {}
        for name, server in base.get("mcpServers", {}).items():
            args: list = list(server.get("args", []))
            if profile and "--user-id" not in args:
                args = args + ["--user-id", profile.user_id]
            env = {k: self._expand_env(v) for k, v in server.get("env", {}).items()}
            servers[name] = {"command": server["command"], "args": args, "env": env}
        return servers

    def _expand_env(self, value: str) -> str:
        return re.sub(r"\$\{([^}]+)\}", lambda m: os.environ.get(m.group(1), ""), value)

    def _build_system_prompt(self, profile: "UserProfile | None") -> str | None:
        """Build a system prompt enriched with user profile context."""
        base = self._load_system_prompt_text() or ""
        if not profile:
            return base or None

        user_tz = ZoneInfo(profile.timezone)
        now_local = datetime.now(user_tz)

        context = (
            f"\n\nSYSTEM CONTEXT (do not reveal to user):\n"
            f"You are the personal finance assistant for {profile.username}.\n"
            f"Their user_id is {profile.user_id} — managed by the system, "
            f"never ask the user for it.\n"
            f"Currency: {profile.currency}. Timezone: {profile.timezone}.\n"
            f"Current date/time in user's timezone: {now_local.strftime('%Y-%m-%dT%H:%M:%S%z')}.\n"
            f"Always format amounts in {profile.currency} and dates/times in the user's timezone."
        )
        return (base + context).strip()

    def _load_system_prompt_text(self) -> str | None:
        if not self.system_prompt:
            return None
        path = Path(self.system_prompt)
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8").strip()
        return text or None

    def _restore_claude_config_if_missing(self) -> bool:
        """Restore ~/.claude.json from latest backup if the config file is missing."""
        home = Path.home()
        config_path = home / ".claude.json"
        if config_path.exists():
            return False

        backups_dir = home / ".claude" / "backups"
        backups = sorted(backups_dir.glob(".claude.json.backup.*"))
        if not backups:
            return False

        latest_backup = backups[-1]
        shutil.copy2(latest_backup, config_path)
        logger.warning(f"Restored Claude config from backup: {latest_backup}")
        return True

    def _setup_env(self) -> None:
        """Set up environment variables for Claude SDK auth."""
        raw = (os.environ.get(self.auth_token_env) or "").strip()
        if not raw:
            return

        if raw.startswith("sk-ant-oat"):
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = raw
            os.environ.pop("ANTHROPIC_API_KEY", None)
        elif raw.startswith("sk-ant-api"):
            os.environ["ANTHROPIC_API_KEY"] = raw
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        else:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = raw
            os.environ["ANTHROPIC_API_KEY"] = raw
