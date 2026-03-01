ALTER TABLE bot_scheduled_tasks
    ADD COLUMN IF NOT EXISTS asset_id UUID;

CREATE INDEX IF NOT EXISTS idx_bot_scheduled_asset
    ON bot_scheduled_tasks(asset_id)
    WHERE asset_id IS NOT NULL;
