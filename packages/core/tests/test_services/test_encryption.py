"""Tests for encryption service."""
import pytest
from flux_core.services.encryption import EncryptionService


def test_encrypt_decrypt_roundtrip():
    svc = EncryptionService("test-secret-key-123")
    plaintext = "my-s3-secret-access-key"
    encrypted = svc.encrypt(plaintext)
    assert encrypted != plaintext
    assert svc.decrypt(encrypted) == plaintext


def test_different_keys_cannot_decrypt():
    svc1 = EncryptionService("key-one")
    svc2 = EncryptionService("key-two")
    encrypted = svc1.encrypt("secret")
    with pytest.raises(Exception):
        svc2.decrypt(encrypted)


def test_encrypt_returns_different_ciphertext_each_time():
    svc = EncryptionService("test-key")
    e1 = svc.encrypt("same-value")
    e2 = svc.encrypt("same-value")
    assert e1 != e2


def test_from_env(monkeypatch):
    monkeypatch.setenv("FLUX_SECRET_KEY", "my-env-secret")
    svc = EncryptionService.from_env()
    assert svc.decrypt(svc.encrypt("test")) == "test"


def test_from_env_missing_key(monkeypatch):
    monkeypatch.delenv("FLUX_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="FLUX_SECRET_KEY"):
        EncryptionService.from_env()
