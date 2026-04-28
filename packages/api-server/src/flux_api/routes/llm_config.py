"""LLM configuration REST routes."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from flux_api.deps import get_db
from flux_core.services.encryption import EncryptionService

router = APIRouter(tags=["llm-config"])


def mask_api_key(plaintext: str) -> str:
    """Safe-for-display masking. Keeps first 4 and last 3 characters."""
    if len(plaintext) < 8:
        return "..."
    return f"{plaintext[:4]}...{plaintext[-3:]}"


class LlmConfigOut(BaseModel):
    user_id: str
    provider: str
    model: str
    base_url: str | None
    api_key_masked: str


class LlmConfigUpdate(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


@router.get("/llm-config")
async def get_llm_config(user_id: str) -> LlmConfigOut:
    """Fetch LLM config for a user."""
    if not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required"
        )

    db = get_db()
    rows = db.fetchall(
        "SELECT user_id, provider, model, base_url, api_key_encrypted "
        "FROM bot_user_llm_config WHERE user_id = ?",
        (user_id,),
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="LLM config not found"
        )

    r = rows[0]
    enc = EncryptionService.from_env()
    api_key = enc.decrypt(r["api_key_encrypted"])

    return LlmConfigOut(
        user_id=r["user_id"],
        provider=r["provider"],
        model=r["model"],
        base_url=r["base_url"],
        api_key_masked=mask_api_key(api_key),
    )


@router.put("/llm-config")
async def update_llm_config(user_id: str, payload: LlmConfigUpdate) -> LlmConfigOut:
    """Create or update LLM config for a user."""
    if not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required"
        )

    db = get_db()
    enc = EncryptionService.from_env()

    # If no api_key provided, try to preserve existing
    api_key = payload.api_key
    if api_key is None:
        rows = db.fetchall(
            "SELECT api_key_encrypted FROM bot_user_llm_config WHERE user_id = ?",
            (user_id,),
        )
        if rows:
            api_key = enc.decrypt(rows[0]["api_key_encrypted"])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="api_key is required for new config",
            )

    encrypted = enc.encrypt(api_key)
    db.execute(
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
        (user_id, payload.provider, payload.model, payload.base_url, encrypted),
    )

    return LlmConfigOut(
        user_id=user_id,
        provider=payload.provider,
        model=payload.model,
        base_url=payload.base_url,
        api_key_masked=mask_api_key(api_key),
    )


@router.delete("/llm-config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(user_id: str) -> None:
    """Delete LLM config for a user."""
    if not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required"
        )

    db = get_db()
    db.execute(
        "DELETE FROM bot_user_llm_config WHERE user_id = ?",
        (user_id,),
    )
