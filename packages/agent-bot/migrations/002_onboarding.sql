-- 002_onboarding.sql
-- Track onboarding progress per user per channel
CREATE TABLE IF NOT EXISTS bot_onboarding (
    platform_id TEXT NOT NULL,
    channel     TEXT NOT NULL,
    step        TEXT NOT NULL DEFAULT 'currency',
    currency    TEXT,
    timezone    TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (platform_id, channel)
);

-- Add platform_id to bot_messages for reply routing (raw numeric platform ID)
ALTER TABLE bot_messages ADD COLUMN IF NOT EXISTS platform_id TEXT;
