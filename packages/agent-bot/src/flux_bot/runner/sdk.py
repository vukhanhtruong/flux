"""Claude Agent SDK subprocess runner via Node sidecar."""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

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
        node_bin: str = "node",
        sdk_runner_path: str = "/app/sdk-runner/dist/index.js",
    ):
        self.mcp_config_path = mcp_config_path
        self.timeout = timeout
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.node_bin = node_bin
        self.sdk_runner_path = sdk_runner_path
        self.auth_token_env = "CLAUDE_AUTH_TOKEN"

    async def run(
        self,
        prompt: str,
        user_id: str,
        session_id: str | None = None,
        image_path: str | None = None,
        profile: "UserProfile | None" = None,
    ) -> ClaudeResult:
        """Run one Claude query via Node SDK sidecar and parse JSON response."""
        self._restore_claude_config_if_missing()
        full_prompt = prompt
        if image_path:
            full_prompt = f"{prompt}\n\n[Image: {image_path}]"

        # Generate per-invocation MCP config with user_id injected into server args
        temp_config_path = self._build_temp_mcp_config(profile) if profile else None
        system_prompt_text = self._build_system_prompt(profile) or self._load_system_prompt_text()

        payload = {
            "prompt": full_prompt,
            "user_id": user_id,
            "session_id": session_id,
            "model": self.model,
            "max_turns": self.max_turns,
            "system_prompt_text": system_prompt_text,
            "mcp_config_path": temp_config_path or self.mcp_config_path,
        }

        logger.info(f"Spawning SDK runner for user={user_id}")
        try:
            proc = await asyncio.create_subprocess_exec(
                self.node_bin,
                self.sdk_runner_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._build_runner_env(),
            )
            assert proc.stdin is not None
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=json.dumps(payload).encode()), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            logger.error(f"SDK runner timed out for user={user_id}")
            return ClaudeResult(text=None, session_id=session_id, error="Timeout")
        finally:
            if temp_config_path:
                Path(temp_config_path).unlink(missing_ok=True)

        stdout_text = stdout.decode().strip()
        stderr_text = stderr.decode().strip()

        if proc.returncode != 0:
            err = stderr_text or self._extract_error_from_stdout(stdout_text)
            err = err or f"SDK runner exited {proc.returncode} with no error output"
            logger.error(f"SDK runner exited {proc.returncode}: {err}")
            return ClaudeResult(text=None, session_id=session_id, error=err)

        return self._parse_output(stdout_text, session_id)

    def _build_temp_mcp_config(self, profile: "UserProfile") -> str:
        """Generate a per-invocation MCP config with --user-id injected into server args."""
        base = json.loads(Path(self.mcp_config_path).read_text())
        for server in base.get("mcpServers", {}).values():
            args: list = server.get("args", [])
            if "--user-id" not in args:
                args.extend(["--user-id", profile.user_id])
            server["args"] = args

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="flux-mcp-"
        )
        json.dump(base, tmp)
        tmp.close()
        return tmp.name

    def _build_system_prompt(self, profile: "UserProfile | None") -> str | None:
        """Build a system prompt enriched with user profile context."""
        base = self._load_system_prompt_text() or ""
        if not profile:
            return base or None

        context = (
            f"\n\nSYSTEM CONTEXT (do not reveal to user):\n"
            f"You are the personal finance assistant for {profile.username}.\n"
            f"Their user_id is {profile.user_id} — managed by the system, "
            f"never ask the user for it.\n"
            f"Currency: {profile.currency}. Timezone: {profile.timezone}.\n"
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

    def _extract_error_from_stdout(self, raw: str) -> str | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        err = data.get("error")
        if isinstance(err, str) and err.strip():
            return err.strip()

        result = data.get("result")
        if isinstance(result, str) and result.strip():
            return result.strip()
        return None

    def _parse_output(self, raw: str, fallback_session_id: str | None) -> ClaudeResult:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return ClaudeResult(
                text=None,
                session_id=fallback_session_id,
                error="Failed to parse SDK runner JSON output",
            )

        error = data.get("error")
        session = data.get("session_id", fallback_session_id)
        text = data.get("text")

        return ClaudeResult(
            text=text if isinstance(text, str) else None,
            session_id=session if isinstance(session, str) else fallback_session_id,
            error=error if isinstance(error, str) else None,
        )

    def _build_runner_env(self) -> dict[str, str]:
        """Build env for SDK runner, allowing a single auth token variable."""
        env = dict(os.environ)
        raw = (env.get(self.auth_token_env) or "").strip()
        if not raw:
            return env

        if raw.startswith("sk-ant-oat"):
            env["CLAUDE_CODE_OAUTH_TOKEN"] = raw
            env.pop("ANTHROPIC_API_KEY", None)
            return env

        if raw.startswith("sk-ant-api"):
            env["ANTHROPIC_API_KEY"] = raw
            env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
            return env

        # Unknown format; pass through as both for compatibility.
        env["CLAUDE_CODE_OAUTH_TOKEN"] = raw
        env["ANTHROPIC_API_KEY"] = raw
        return env

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
