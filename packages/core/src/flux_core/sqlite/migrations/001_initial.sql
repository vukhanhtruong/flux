-- Users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    display_name TEXT,
    platform TEXT,
    categories TEXT DEFAULT '["Food","Transport","Housing","Utilities","Entertainment","Health","Shopping","Salary","Investment","Other"]',
    username TEXT,
    currency TEXT DEFAULT 'VND',
    timezone TEXT DEFAULT 'Asia/Ho_Chi_Minh',
    platform_id TEXT,
    locale TEXT DEFAULT 'vi-VN',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Transactions (NO embedding column — embeddings in zvec)
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    amount TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    is_recurring INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, date);
CREATE INDEX IF NOT EXISTS idx_txn_user_category ON transactions(user_id, category);

-- Budgets
CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    category TEXT NOT NULL,
    monthly_limit TEXT NOT NULL,
    UNIQUE(user_id, category)
);

-- Savings Goals
CREATE TABLE IF NOT EXISTS savings_goals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    target_amount TEXT NOT NULL,
    current_amount TEXT DEFAULT '0',
    deadline TEXT,
    color TEXT DEFAULT '#3B82F6'
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    amount TEXT NOT NULL,
    billing_cycle TEXT NOT NULL CHECK (billing_cycle IN ('monthly', 'yearly')),
    next_date TEXT NOT NULL,
    category TEXT NOT NULL,
    active INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_subs_user_active ON subscriptions(user_id, active);

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    amount TEXT NOT NULL,
    interest_rate TEXT DEFAULT '0',
    frequency TEXT CHECK (frequency IN ('monthly', 'quarterly', 'yearly')),
    next_date TEXT NOT NULL,
    category TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    asset_type TEXT CHECK (asset_type IN ('income', 'savings')),
    principal_amount TEXT,
    compound_frequency TEXT CHECK (compound_frequency IN ('monthly', 'quarterly', 'yearly')),
    maturity_date TEXT,
    start_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_assets_user_active ON assets(user_id, active);

-- Agent Memory (NO embedding column)
CREATE TABLE IF NOT EXISTS agent_memory (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    memory_type TEXT NOT NULL CHECK (memory_type IN ('conversation', 'fact', 'preference')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_memory_user ON agent_memory(user_id);

-- Bot Messages
CREATE TABLE IF NOT EXISTS bot_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    platform_id TEXT,
    text TEXT,
    image_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_bot_msg_status ON bot_messages(status, created_at);

-- Bot Sessions
CREATE TABLE IF NOT EXISTS bot_sessions (
    user_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Bot Scheduled Tasks
CREATE TABLE IF NOT EXISTS bot_scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    schedule_type TEXT NOT NULL CHECK (schedule_type IN ('once', 'cron', 'interval')),
    schedule_value TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
    next_run_at TEXT NOT NULL,
    last_run_at TEXT,
    subscription_id TEXT,
    asset_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sched_status ON bot_scheduled_tasks(status, next_run_at);

-- Bot Outbound Messages
CREATE TABLE IF NOT EXISTS bot_outbound_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    sender TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbound_status ON bot_outbound_messages(status);
