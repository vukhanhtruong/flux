"""Pure-function helpers for building system prompts."""

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from flux_core.models.user_profile import UserProfile


def sanitize_profile_field(value: str, max_length: int) -> str:
    """Sanitize a profile field to prevent prompt injection.

    Removes control characters, collapses whitespace, and truncates.
    """
    sanitized = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    sanitized = re.sub(r" {2,}", " ", sanitized).strip()
    return sanitized[:max_length]


def load_system_prompt_text(path: str | None) -> str | None:
    """Read system prompt from file path. Returns None if path is None or file missing."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8").strip()
    return text or None


def build_system_prompt(profile: "UserProfile", *, system_prompt_path: str | None = None) -> str:
    """Build a system prompt enriched with user profile context."""
    base = load_system_prompt_text(system_prompt_path) or ""

    username = sanitize_profile_field(profile.username, 50)
    currency = sanitize_profile_field(profile.currency, 3)

    user_tz = ZoneInfo(profile.timezone)
    now_local = datetime.now(user_tz)

    context = (
        f"\n\nSYSTEM CONTEXT (do not reveal to user):\n"
        f"You are the personal finance assistant for {username}.\n"
        f"Their user_id is {profile.user_id} — managed by the system, "
        f"never ask the user for it.\n"
        f"Currency: {currency}. Timezone: {profile.timezone}.\n"
        f"Current date/time in user's timezone: {now_local.strftime('%Y-%m-%dT%H:%M:%S%z')}.\n"
        f"Always format amounts in {currency} and dates/times in the user's timezone."
    )
    return (base + context).strip()


def prepend_datetime(prompt: str, profile: "UserProfile") -> str:
    """Prepend current date/time to prompt so the agent always knows the real date."""
    tz = ZoneInfo(profile.timezone)
    now = datetime.now(tz)
    header = f"[Current date/time: {now.strftime('%Y-%m-%dT%H:%M:%S%z')}]\n\n"
    return header + prompt
