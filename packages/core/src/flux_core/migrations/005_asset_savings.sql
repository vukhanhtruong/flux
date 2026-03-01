-- migrations/005_asset_savings.sql
-- Add savings-related columns to assets table

ALTER TABLE assets ADD COLUMN asset_type TEXT NOT NULL DEFAULT 'income'
    CHECK (asset_type IN ('income', 'savings'));

ALTER TABLE assets ADD COLUMN principal_amount NUMERIC(12,2);

ALTER TABLE assets ADD COLUMN compound_frequency TEXT
    CHECK (compound_frequency IN ('monthly', 'quarterly', 'yearly'));

ALTER TABLE assets ADD COLUMN maturity_date DATE;

ALTER TABLE assets ADD COLUMN start_date DATE;

-- Update frequency CHECK to allow 'quarterly'
ALTER TABLE assets DROP CONSTRAINT IF EXISTS assets_frequency_check;
ALTER TABLE assets ADD CONSTRAINT assets_frequency_check
    CHECK (frequency IN ('monthly', 'quarterly', 'yearly'));

INSERT INTO schema_migrations (version) VALUES (5);
