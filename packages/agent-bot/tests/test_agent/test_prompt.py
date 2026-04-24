from flux_core.models.user_profile import UserProfile
from flux_bot.agent.prompt import (
    sanitize_profile_field,
    build_system_prompt,
    prepend_datetime,
)


def _profile(**kw):
    defaults = dict(
        user_id="tg:1",
        username="alice",
        currency="USD",
        timezone="UTC",
        locale="en",
        channel="telegram",
        platform_id="1",
    )
    return UserProfile(**{**defaults, **kw})


def test_sanitize_strips_control_chars():
    assert "\x00" not in sanitize_profile_field("a\x00b", 100)
    assert sanitize_profile_field("  hello  world  ", 100) == "hello world"


def test_sanitize_truncates():
    assert len(sanitize_profile_field("x" * 200, 10)) == 10


def test_build_system_prompt_includes_username():
    p = _profile(username="alice")
    out = build_system_prompt(p)
    assert "alice" in out


def test_build_system_prompt_includes_currency():
    p = _profile(currency="EUR")
    out = build_system_prompt(p)
    assert "EUR" in out


def test_prepend_datetime_contains_iso_date():
    p = _profile(timezone="UTC")
    out = prepend_datetime("hello", p)
    import re

    assert re.search(r"\d{4}-\d{2}-\d{2}T", out)
    assert out.endswith("hello")
