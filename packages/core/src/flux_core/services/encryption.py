"""Fernet encryption service for sensitive config values."""
from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class EncryptionService:
    _SALT = b"flux-finance-config-v1"

    def __init__(self, secret_key: str):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._SALT,
            iterations=480_000,
        )
        derived = kdf.derive(secret_key.encode())
        self._fernet = Fernet(base64.urlsafe_b64encode(derived))

    @classmethod
    def from_env(cls) -> EncryptionService:
        key = os.getenv("FLUX_SECRET_KEY")
        if not key:
            raise ValueError(
                "FLUX_SECRET_KEY environment variable is required for encryption. "
                "Set it to a strong, unique secret string."
            )
        return cls(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
