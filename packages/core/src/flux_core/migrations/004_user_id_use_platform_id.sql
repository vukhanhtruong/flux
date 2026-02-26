-- 004: Change user_id from "tg:<username>" to "tg:<platform_id>"
-- Fixes message routing: platform_id is the numeric Telegram ID needed for API calls.

DO $$
DECLARE
    r RECORD;
    new_id TEXT;
    prefix TEXT;
    tbl TEXT;
    -- All tables that may contain a user_id column referencing users.id
    all_tables TEXT[] := ARRAY[
        'transactions', 'budgets', 'savings_goals', 'subscriptions',
        'assets', 'agent_memory',
        'bot_messages', 'bot_sessions', 'bot_scheduled_tasks',
        'bot_outbound_messages'
    ];
BEGIN
    -- Disable triggers on all existing tables to bypass FK checks
    FOREACH tbl IN ARRAY all_tables
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = tbl AND table_schema = 'public'
        ) THEN
            EXECUTE format('ALTER TABLE %I DISABLE TRIGGER ALL', tbl);
        END IF;
    END LOOP;

    -- Rewrite user_id values
    FOR r IN SELECT id, platform, platform_id FROM users WHERE platform_id IS NOT NULL
    LOOP
        prefix := CASE r.platform
            WHEN 'telegram' THEN 'tg'
            WHEN 'whatsapp' THEN 'wa'
            ELSE r.platform
        END;
        new_id := prefix || ':' || r.platform_id;

        IF r.id != new_id THEN
            FOREACH tbl IN ARRAY all_tables
            LOOP
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = tbl AND table_schema = 'public'
                ) THEN
                    EXECUTE format(
                        'UPDATE %I SET user_id = $1 WHERE user_id = $2', tbl
                    ) USING new_id, r.id;
                END IF;
            END LOOP;

            UPDATE users SET id = new_id WHERE id = r.id;
        END IF;
    END LOOP;

    -- Re-enable triggers
    FOREACH tbl IN ARRAY all_tables
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = tbl AND table_schema = 'public'
        ) THEN
            EXECUTE format('ALTER TABLE %I ENABLE TRIGGER ALL', tbl);
        END IF;
    END LOOP;
END $$;

INSERT INTO schema_migrations (version) VALUES (4);
