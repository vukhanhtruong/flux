-- Additional indexes for query performance.
CREATE INDEX IF NOT EXISTS idx_goals_user ON savings_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_sched_asset ON bot_scheduled_tasks(asset_id);
CREATE INDEX IF NOT EXISTS idx_sched_sub ON bot_scheduled_tasks(subscription_id);
