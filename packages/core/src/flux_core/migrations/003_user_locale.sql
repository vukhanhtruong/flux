-- 003_user_locale.sql
-- Add locale preference to user profile
ALTER TABLE users ADD COLUMN IF NOT EXISTS locale TEXT NOT NULL DEFAULT 'vi-VN';

INSERT INTO schema_migrations (version) VALUES (3);
