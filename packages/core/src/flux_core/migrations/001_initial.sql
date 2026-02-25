-- migrations/001_initial.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  display_name TEXT,
  platform TEXT NOT NULL,
  categories TEXT[] DEFAULT ARRAY[
    'Food', 'Transport', 'Housing', 'Utilities', 'Entertainment',
    'Health', 'Shopping', 'Salary', 'Investment', 'Other'
  ],
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
  is_recurring BOOLEAN DEFAULT FALSE,
  tags TEXT[] DEFAULT '{}',
  embedding vector(384),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE budgets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  category TEXT NOT NULL,
  monthly_limit NUMERIC(12,2) NOT NULL CHECK (monthly_limit > 0),
  UNIQUE(user_id, category)
);

CREATE TABLE savings_goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  target_amount NUMERIC(12,2) NOT NULL CHECK (target_amount > 0),
  current_amount NUMERIC(12,2) DEFAULT 0 CHECK (current_amount >= 0),
  deadline DATE,
  color TEXT DEFAULT '#3B82F6'
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  billing_cycle TEXT NOT NULL CHECK (billing_cycle IN ('monthly', 'yearly')),
  next_date DATE NOT NULL,
  category TEXT NOT NULL,
  active BOOLEAN DEFAULT TRUE
);

CREATE TABLE assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  interest_rate NUMERIC(5,2) DEFAULT 0,
  frequency TEXT NOT NULL CHECK (frequency IN ('monthly', 'yearly')),
  next_date DATE NOT NULL,
  category TEXT NOT NULL,
  active BOOLEAN DEFAULT TRUE
);

CREATE TABLE agent_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  memory_type TEXT NOT NULL CHECK (memory_type IN ('conversation', 'fact', 'preference')),
  content TEXT NOT NULL,
  embedding vector(384),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schema version tracking
CREATE TABLE schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_txn_user_date ON transactions(user_id, date DESC);
CREATE INDEX idx_txn_user_category ON transactions(user_id, category);
CREATE INDEX idx_txn_embedding ON transactions
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memory_user ON agent_memory(user_id);
CREATE INDEX idx_memory_embedding ON agent_memory
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_subs_user_active ON subscriptions(user_id, active);
CREATE INDEX idx_assets_user_active ON assets(user_id, active);

INSERT INTO schema_migrations (version) VALUES (1);
