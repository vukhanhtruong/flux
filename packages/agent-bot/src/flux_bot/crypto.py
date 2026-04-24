"""Fernet-based encryption for per-user LLM API keys.

Keys are derived from FLUX_SECRET_KEY via SHA-256 so any secret length works.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet


def derive_fernet_key() -> bytes:
    secret = os.environ.get("FLUX_SECRET_KEY")
    if not secret:
        raise RuntimeError("FLUX_SECRET_KEY environment variable is required")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_api_key(plaintext: str) -> str:
    f = Fernet(derive_fernet_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_api_key(ciphertext: str) -> str:
    f = Fernet(derive_fernet_key())
    return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")


def mask_api_key(plaintext: str) -> str:
    """Safe-for-display masking. Keeps first 4 and last 4 characters."""
    if len(plaintext) <= 8:
        return "…" + plaintext[-4:]
    return f"{plaintext[:4]}…{plaintext[-4:]}"
