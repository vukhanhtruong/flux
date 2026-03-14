-- Add 'at_maturity' to frequency and compound_frequency CHECK constraints.
-- SQLite does not support ALTER CHECK, so recreate the table.
CREATE TABLE IF NOT EXISTS assets_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    amount TEXT NOT NULL,
    interest_rate TEXT DEFAULT '0',
    frequency TEXT CHECK (frequency IN ('monthly', 'quarterly', 'yearly', 'at_maturity')),
    next_date TEXT NOT NULL,
    category TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    asset_type TEXT CHECK (asset_type IN ('income', 'savings')),
    principal_amount TEXT,
    compound_frequency TEXT CHECK (compound_frequency IN ('monthly', 'quarterly', 'yearly', 'at_maturity')),
    maturity_date TEXT,
    start_date TEXT
);

INSERT INTO assets_new SELECT * FROM assets;
DROP TABLE assets;
ALTER TABLE assets_new RENAME TO assets;
CREATE INDEX IF NOT EXISTS idx_assets_user_active ON assets(user_id, active);
