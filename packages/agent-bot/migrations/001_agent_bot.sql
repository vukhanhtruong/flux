CREATE TABLE IF NOT EXISTS bot_messages (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    text TEXT,
    image_path TEXT,
    status TEXT DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bot_messages_status ON bot_messages(status, created_at);
CREATE INDEX IF NOT EXISTS idx_bot_messages_user ON bot_messages(user_id);

CREATE TABLE IF NOT EXISTS bot_sessions (
    user_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_scheduled_tasks (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    schedule_value TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_task_run_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES bot_scheduled_tasks(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT,
    error TEXT
);
