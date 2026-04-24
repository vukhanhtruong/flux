-- Per-user LLM provider/model/endpoint + Fernet-encrypted API key.
-- Managed by UserLlmConfigRepository in packages/agent-bot.

CREATE TABLE IF NOT EXISTS bot_user_llm_config (
    user_id           TEXT PRIMARY KEY,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    base_url          TEXT,
    api_key_encrypted TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bot_user_llm_config_provider
    ON bot_user_llm_config(provider);
