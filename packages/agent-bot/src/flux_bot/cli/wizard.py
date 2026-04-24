"""Interactive prompt helpers for the flux CLI.

All wizard functions accept pre-constructed repositories so they are
independently testable without touching argparse or the database bootstrap
(which wraps everything in asyncio.run).

Public API
----------
config_llm(db, llm_config_repo)  — configure LLM provider / model / key
onboard(db, profile_repo)         — configure currency / timezone / username

Raises
------
CliError — user-facing error with a plain English message (no tracebacks).
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from flux_bot.db.llm_config import UserLlmConfigRepository
    from flux_bot.db.profile import ProfileRepository
    from flux_core.sqlite.database import Database

console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

CLI_USER_ID = "cli:local"
CLI_CHANNEL = "cli"
CLI_PLATFORM_ID = "local"

VALID_PROVIDERS = ("anthropic", "openai", "groq", "openrouter", "custom")

_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "groq": "llama-3.1-70b-versatile",
}

# Providers that require an explicit base_url
_REQUIRE_BASE_URL = {"custom"}


# ──────────────────────────────────────────────────────────────────────────────
# Error type
# ──────────────────────────────────────────────────────────────────────────────

class CliError(Exception):
    """User-facing CLI error.  main() catches this and prints it cleanly."""


# ──────────────────────────────────────────────────────────────────────────────
# Shared prompt helper — thin wrapper so tests can monkeypatch `builtins.input`
# ──────────────────────────────────────────────────────────────────────────────

def _prompt(message: str) -> str:
    """Read a line from stdin.  Delegates to builtin input() for easy mocking."""
    return input(message)


# ──────────────────────────────────────────────────────────────────────────────
# config llm wizard
# ──────────────────────────────────────────────────────────────────────────────

async def config_llm(db: "Database", llm_config_repo: "UserLlmConfigRepository") -> None:
    """Interactive wizard: configure LLM provider / model / API key.

    Persists to ``bot_user_llm_config`` for user ``cli:local``.

    Raises
    ------
    CliError
        If ``FLUX_SECRET_KEY`` is not set or the chosen provider is invalid.
    """
    # Validate FLUX_SECRET_KEY early — give a clear message before prompting.
    if not os.getenv("FLUX_SECRET_KEY"):
        raise CliError(
            "FLUX_SECRET_KEY environment variable is required for encrypting your API key.\n"
            "Set it to a strong, unique secret of at least 32 characters:\n"
            "  export FLUX_SECRET_KEY='<your-secret>'"
        )

    providers_str = "/".join(VALID_PROVIDERS)
    provider = _prompt(f"LLM Provider? [{providers_str}]: ").strip()
    if not provider:
        provider = "anthropic"

    if provider not in VALID_PROVIDERS:
        raise CliError(
            f"Invalid provider {provider!r}. "
            f"Choose one of: {', '.join(VALID_PROVIDERS)}"
        )

    # Model — show default in brackets if one exists
    default_model = _DEFAULT_MODELS.get(provider, "")
    model_prompt = f"Model? [{default_model}]: " if default_model else "Model: "
    model_raw = _prompt(model_prompt).strip()
    model = model_raw if model_raw else default_model
    if not model:
        raise CliError("Model is required for this provider.")

    api_key = _prompt("API Key: ").strip()
    if not api_key:
        raise CliError("API key cannot be empty.")

    # base_url
    base_url_raw = _prompt("Base URL (leave empty for default): ").strip()
    base_url: str | None = base_url_raw if base_url_raw else None

    if provider in _REQUIRE_BASE_URL and not base_url:
        raise CliError(f"Base URL is required for provider {provider!r}.")

    # Persist — upsert uses encrypt_api_key internally
    from flux_bot.db.llm_config import UserLlmConfig

    cfg = UserLlmConfig(
        user_id=CLI_USER_ID,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
    await llm_config_repo.upsert(cfg)

    console.print(f"[green]✓ LLM configured.[/green] Provider: {provider}, Model: {model}")


# ──────────────────────────────────────────────────────────────────────────────
# onboard wizard
# ──────────────────────────────────────────────────────────────────────────────

async def onboard(db: "Database", profile_repo: "ProfileRepository") -> None:
    """Interactive wizard: configure user profile (username / currency / timezone).

    Creates or updates the profile for ``cli:local``.
    """
    username_raw = _prompt(f"Username [{CLI_USER_ID}]: ").strip()
    username = username_raw if username_raw else CLI_USER_ID

    currency_raw = _prompt("Currency [USD]: ").strip()
    currency = currency_raw if currency_raw else "USD"

    timezone_raw = _prompt("Timezone [UTC]: ").strip()
    timezone = timezone_raw if timezone_raw else "UTC"

    # Upsert: try get → create if missing, then update.
    existing = await profile_repo.get_by_user_id(CLI_USER_ID)
    if existing is None:
        from flux_core.models.user_profile import UserProfileCreate

        create = UserProfileCreate(
            username=username,
            channel=CLI_CHANNEL,
            platform_id=CLI_PLATFORM_ID,
            currency=currency,
            timezone=timezone,
            locale="en-US",
        )
        await profile_repo.create(create)
    else:
        await profile_repo.update(
            CLI_USER_ID,
            username=username,
            currency=currency,
            timezone=timezone,
        )

    console.print(
        f"[green]✓ Profile saved.[/green] "
        f"Username: {username}, Currency: {currency}, Timezone: {timezone}"
    )
