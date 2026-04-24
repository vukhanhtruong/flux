"""Tests for the typed LlmConfigMissingError exception."""
from flux_bot.db.llm_config import LlmConfigMissingError


def test_exception_exists_and_carries_user_id():
    err = LlmConfigMissingError("tg:42")
    assert err.user_id == "tg:42"
    assert "tg:42" in str(err)
