"""Claude Code CLI subprocess runner."""

import asyncio
import json
import structlog
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = structlog.get_logger(__name__)


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

    async def run(
        self,
        prompt: str,
        user_id: str,
        session_id: str | None = None,
        image_path: str | None = None,
    ) -> ClaudeResult:
        """Spawn claude CLI and return the result."""
        cmd = self._build_command(prompt, user_id, session_id, image_path)
        self._restore_claude_config_if_missing()
        logger.info(f"Spawning Claude CLI for user={user_id}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            logger.error(f"Claude CLI timed out for user={user_id}")
            return ClaudeResult(text=None, session_id=session_id, error="Timeout")

        if proc.returncode != 0:
            stderr_text = stderr.decode().strip()
            stdout_text = stdout.decode().strip()
            err = (
                stderr_text
                or self._extract_error_from_stdout(stdout_text)
                or f"Claude CLI exited {proc.returncode} with no error output"
            )
            logger.error(f"Claude CLI exited {proc.returncode}: {err}")
            return ClaudeResult(text=None, session_id=session_id, error=err)

        return self._parse_output(stdout.decode(), session_id)

    def _build_command(
        self,
        prompt: str,
        user_id: str,
        session_id: str | None,
        image_path: str | None,
    ) -> list[str]:
        """Build the claude CLI command."""
        full_prompt = prompt
        if image_path:
            full_prompt = f"{prompt}\n\n[Image: {image_path}]"

        cmd = [
            "claude",
            "-p", full_prompt,
            "--output-format", "json",
            "--mcp-config", self.mcp_config_path,
            "--max-turns", str(self.max_turns),
            "--append-system-prompt", f"The current user_id is: {user_id}",
        ]

        if self._should_skip_permissions():
            cmd.append("--dangerously-skip-permissions")

        if session_id:
            cmd.extend(["--resume", session_id])

        if self.model:
            cmd.extend(["--model", self.model])

        if self.system_prompt:
            cmd.extend(["--system-prompt-file", self.system_prompt])

        return cmd

    def _should_skip_permissions(self) -> bool:
        """Claude CLI forbids --dangerously-skip-permissions when running as root."""
        geteuid = getattr(os, "geteuid", None)
        return not callable(geteuid) or geteuid() != 0

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

    def _extract_error_from_stdout(self, raw: str) -> str | None:
        """Extract error text from Claude JSON output emitted on stdout."""
        if not raw:
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        result_text = data.get("result")
        if isinstance(result_text, str) and result_text.strip():
            return result_text.strip()
        return None

    def _parse_output(self, raw: str, fallback_session_id: str | None) -> ClaudeResult:
        """Parse Claude CLI JSON output."""
        try:
            data = json.loads(raw)
            return ClaudeResult(
                text=data.get("result", ""),
                session_id=data.get("session_id", fallback_session_id),
            )
        except json.JSONDecodeError:
            return ClaudeResult(
                text=raw.strip() or None,
                session_id=fallback_session_id,
                error="Failed to parse JSON output" if not raw.strip() else None,
            )
