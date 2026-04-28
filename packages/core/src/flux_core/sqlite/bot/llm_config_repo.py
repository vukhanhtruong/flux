"""Per-user LLM config repository for api-server.

Reuses the same bot_user_llm_config table as agent-bot,
with encryption for API keys.
"""
from __future__ import annotations

from dataclasses import dataclass

from flux_core.services.encryption import EncryptionService
from flux_core.sqlite.database import Database


def mask_api_key(plaintext: str) -> str:
    """Safe-for-display masking. Keeps first 4 and last 4 characters."""
    if len(plaintext) < 8:
        return "..."
    return f"{plaintext[:4]}...{plaintext[-4:]}"


@dataclass
class LlmConfig:
    user_id: str
    provider: str
    model: str
    base_url: str | None
    api_key: str


class SqliteLlmConfigRepository:
    """SQLite repository for per-user LLM configuration."""

    def __init__(self, db: Database, *, encryption_key: str | None = None):
        self._db = db
        self._encryption_svc = (
            EncryptionService(encryption_key)
            if encryption_key
            else EncryptionService.from_env()
        )

    def get(self, user_id: str) -> LlmConfig | None:
        """Fetch LLM config for a user, decrypting the API key."""
        rows = self._db.fetchall(
            "SELECT user_id, provider, model, base_url, api_key_encrypted "
            "FROM bot_user_llm_config WHERE user_id = ?",
            (user_id,),
        )
        if not rows:
            return None
        r = rows[0]
        return LlmConfig(
            user_id=r["user_id"],
            provider=r["provider"],
            model=r["model"],
            base_url=r["base_url"],
            api_key=self._encryption_svc.decrypt(r["api_key_encrypted"]),
        )

    def upsert(self, cfg: LlmConfig) -> None:
        """Insert or update LLM config, encrypting the API key."""
        encrypted = self._encryption_svc.encrypt(cfg.api_key)
        self._db.execute(
            """
            INSERT INTO bot_user_llm_config
                (user_id, provider, model, base_url, api_key_encrypted)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                provider = excluded.provider,
                model = excluded.model,
                base_url = excluded.base_url,
                api_key_encrypted = excluded.api_key_encrypted,
                updated_at = datetime('now')
            """,
            (cfg.user_id, cfg.provider, cfg.model, cfg.base_url, encrypted),
        )

    def delete(self, user_id: str) -> None:
        """Remove LLM config for a user."""
        self._db.execute(
            "DELETE FROM bot_user_llm_config WHERE user_id = ?",
            (user_id,),
        )
