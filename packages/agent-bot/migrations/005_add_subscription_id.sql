ALTER TABLE bot_scheduled_tasks
    ADD COLUMN IF NOT EXISTS subscription_id UUID;

CREATE INDEX IF NOT EXISTS idx_bot_scheduled_sub
    ON bot_scheduled_tasks(subscription_id)
    WHERE subscription_id IS NOT NULL;
