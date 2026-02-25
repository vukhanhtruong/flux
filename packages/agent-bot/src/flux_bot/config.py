"""Agent bot configuration loader."""

import os
from dataclasses import dataclass, field
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    allow_from: list[str] = field(default_factory=list)


@dataclass
class RunnerConfig:
    timeout: int = 300
    max_turns: int = 10
    model: str | None = None
    mcp_config_path: str = "/app/mcp-config.json"
    system_prompt_path: str = str(_SRC_DIR / "system-prompt.txt")


@dataclass
class BotConfig:
    database_url: str = "postgresql://localhost/flux"
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    poll_interval: float = 2.0
    fallback_poll_interval: float = 30.0
    image_dir: str = "/tmp/flux-images"


def load_config() -> BotConfig:
    """Load config from environment variables."""
    config = BotConfig()

    config.database_url = os.getenv("DATABASE_URL", config.database_url)
    config.poll_interval = float(os.getenv("POLL_INTERVAL", str(config.poll_interval)))
    config.fallback_poll_interval = float(
        os.getenv("FALLBACK_POLL_INTERVAL", str(config.fallback_poll_interval))
    )
    config.image_dir = os.getenv("IMAGE_DIR", config.image_dir)

    # Telegram
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if telegram_token and ":" in telegram_token:
        config.telegram.bot_token = telegram_token
        config.telegram.enabled = True
    allow_from = os.getenv("TELEGRAM_ALLOW_FROM", "")
    if allow_from:
        config.telegram.allow_from = [s.strip() for s in allow_from.split(",")]

    # Runner
    config.runner.timeout = int(os.getenv("CLAUDE_TIMEOUT", str(config.runner.timeout)))
    config.runner.max_turns = int(os.getenv("CLAUDE_MAX_TURNS", str(config.runner.max_turns)))
    config.runner.model = os.getenv("CLAUDE_MODEL") or config.runner.model
    config.runner.mcp_config_path = os.getenv(
        "MCP_CONFIG_PATH", config.runner.mcp_config_path
    )
    config.runner.system_prompt_path = os.getenv(
        "SYSTEM_PROMPT_PATH", config.runner.system_prompt_path
    )

    return config
