-- Tarasca migration 004: email ingestion (near-real-time card expenses)
-- Run this in the Supabase SQL Editor if you already created the tables
-- with a previous schema (supabase_schema.sql).

-- 1. Track where each transaction came from: extracto (bank file) | email
--    (card-use notification) | manual. Existing rows default to 'extracto'.
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'extracto';

ALTER TABLE transactions
    DROP CONSTRAINT IF EXISTS transactions_source_check;

ALTER TABLE transactions
    ADD CONSTRAINT transactions_source_check
    CHECK (source IN ('extracto', 'email', 'manual'));

-- 2. Key/value state for the email poller (last processed IMAP UID, etc.)
CREATE TABLE IF NOT EXISTS ingest_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. (Optional) speeds up the source filter on the transactions page
CREATE INDEX IF NOT EXISTS idx_transactions_source
    ON transactions(source);
