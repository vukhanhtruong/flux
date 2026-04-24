"""Tests for encryption facade over `flux_core.services.encryption`."""
import pytest

from flux_bot.crypto import (
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
)


@pytest.fixture
def flux_secret(monkeypatch):
    monkeypatch.setenv("FLUX_SECRET_KEY", "test-secret-key-for-tests-0123456789")
    yield


def test_roundtrip(flux_secret):
    enc = encrypt_api_key("sk-ant-api-abcd1234")
    assert enc != "sk-ant-api-abcd1234"
    assert decrypt_api_key(enc) == "sk-ant-api-abcd1234"


def test_wrong_secret_fails(flux_secret, monkeypatch):
    enc = encrypt_api_key("sk-ant-api-abcd1234")
    monkeypatch.setenv("FLUX_SECRET_KEY", "different-secret-0123456789abcd")
    with pytest.raises(Exception):  # InvalidToken
        decrypt_api_key(enc)


def test_missing_secret_raises(monkeypatch):
    monkeypatch.delenv("FLUX_SECRET_KEY", raising=False)
    # EncryptionService.from_env raises ValueError when FLUX_SECRET_KEY is absent.
    with pytest.raises(ValueError, match="FLUX_SECRET_KEY"):
        encrypt_api_key("whatever")


def test_mask_shows_last_four():
    assert mask_api_key("sk-ant-api-abcd1234") == "sk-a…1234"
    assert mask_api_key("short") == "…hort"
