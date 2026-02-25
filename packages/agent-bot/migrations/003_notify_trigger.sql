CREATE OR REPLACE FUNCTION notify_new_bot_message()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('new_bot_message', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_new_bot_message'
    ) THEN
        CREATE TRIGGER trg_new_bot_message
        AFTER INSERT ON bot_messages
        FOR EACH ROW
        EXECUTE FUNCTION notify_new_bot_message();
    END IF;
END;
$$;
