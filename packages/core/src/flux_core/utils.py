"""Shared utility functions."""
from datetime import UTC, date, datetime


def to_utc_midnight(d: date) -> datetime:
    """Convert a date to UTC midnight datetime."""
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def build_savings_prompt(name: str, asset_id: str, is_maturity: bool) -> str:
    """Build a prompt string for savings interest processing."""
    base = f"Process savings interest for {name} (id: {asset_id})"
    if is_maturity:
        return (
            f"{base}. This deposit matures today. "
            "After processing, inform the user about the final balance "
            "and ask if they'd like to withdraw."
        )
    return base
