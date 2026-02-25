-- 002_user_profiles.sql
-- Extend users table with onboarding profile fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'VND';
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh';
ALTER TABLE users ADD COLUMN IF NOT EXISTS platform_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_channel_username ON users (platform, username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_channel_platform_id ON users (platform, platform_id);

INSERT INTO schema_migrations (version) VALUES (2);
