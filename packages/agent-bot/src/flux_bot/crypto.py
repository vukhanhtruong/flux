"""Encryption facade for per-user LLM API keys.

Delegates to the canonical `flux_core.services.encryption.EncryptionService`
so there is exactly one KDF derived from `FLUX_SECRET_KEY` in the project.
Keeps a local `mask_api_key` helper (a display concern, not crypto).
"""
from flux_core.services.encryption import EncryptionService


def encrypt_api_key(plaintext: str) -> str:
    return EncryptionService.from_env().encrypt(plaintext)


def decrypt_api_key(ciphertext: str) -> str:
    return EncryptionService.from_env().decrypt(ciphertext)


def mask_api_key(plaintext: str) -> str:
    """Safe-for-display masking. Keeps first 4 and last 4 characters.

    Inputs shorter than 8 characters collapse to a single ellipsis —
    showing any suffix from a short value would leak a disproportionate
    fraction of the secret.
    """
    if len(plaintext) < 8:
        return "…"
    return f"{plaintext[:4]}…{plaintext[-4:]}"
