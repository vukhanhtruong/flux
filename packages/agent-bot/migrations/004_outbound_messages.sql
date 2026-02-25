CREATE TABLE IF NOT EXISTS bot_outbound_messages (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    sender TEXT,
    status TEXT DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bot_outbound_status
    ON bot_outbound_messages(status, created_at);

CREATE OR REPLACE FUNCTION notify_outbound_message()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('new_outbound_message', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_outbound_message'
          AND tgrelid = 'bot_outbound_messages'::regclass
    ) THEN
        CREATE TRIGGER trg_outbound_message
        AFTER INSERT ON bot_outbound_messages
        FOR EACH ROW
        EXECUTE FUNCTION notify_outbound_message();
    END IF;
END;
$$;
