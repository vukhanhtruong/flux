"""Per-user LLM config: provider, model, endpoint, encrypted API key.

The underlying flux_core.sqlite.Database exposes synchronous execute/
fetchall/fetchone; we wrap them in async methods to match the rest of
the flux_bot.db repository style (see sessions.py, messages.py, etc.).
"""
from dataclasses import dataclass

from flux_bot.crypto import decrypt_api_key, encrypt_api_key, mask_api_key
from flux_core.sqlite.database import Database


@dataclass
class UserLlmConfig:
    user_id: str
    provider: str
    model: str
    base_url: str | None
    api_key: str  # plaintext in memory only

    def __repr__(self) -> str:
        return (
            f"UserLlmConfig(user_id={self.user_id!r}, provider={self.provider!r}, "
            f"model={self.model!r}, base_url={self.base_url!r}, "
            f"api_key={mask_api_key(self.api_key)!r})"
        )


class UserLlmConfigRepository:
    def __init__(self, db: Database):
        self._db = db

    async def get(self, user_id: str) -> UserLlmConfig | None:
        rows = self._db.fetchall(
            "SELECT user_id, provider, model, base_url, api_key_encrypted "
            "FROM bot_user_llm_config WHERE user_id = ?",
            (user_id,),
        )
        if not rows:
            return None
        r = rows[0]
        return UserLlmConfig(
            user_id=r["user_id"],
            provider=r["provider"],
            model=r["model"],
            base_url=r["base_url"],
            api_key=decrypt_api_key(r["api_key_encrypted"]),
        )

    async def upsert(self, cfg: UserLlmConfig) -> None:
        # flux_core.sqlite.Database opens with isolation_level=None
        # (autocommit), so DML statements persist without explicit commit.
        enc = encrypt_api_key(cfg.api_key)
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
            (cfg.user_id, cfg.provider, cfg.model, cfg.base_url, enc),
        )

    async def delete(self, user_id: str) -> None:
        self._db.execute(
            "DELETE FROM bot_user_llm_config WHERE user_id = ?",
            (user_id,),
        )


class LlmConfigMissingError(Exception):
    """Raised when a user's LLM config is not found.

    Carries the offending user_id so upstream handlers can prompt them
    to run `/settings llm` (or the equivalent CLI command).
    """

    def __init__(self, user_id: str):
        super().__init__(
            f"No LLM config for user_id={user_id}. Run /settings llm to set one up."
        )
        self.user_id = user_id
