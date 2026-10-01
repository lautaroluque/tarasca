-- Tarasca migration 002: movement types + free-form currencies
-- Run this in the Supabase SQL Editor if you already created the tables
-- with the previous schema (supabase_schema.sql).

-- 1. Allow any currency (USDT, USDC, BUSD...) instead of only ARS/USD
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_currency_check;

-- 2. Add the movement type: ingreso | gasto | transferencia
--    Existing rows default to 'gasto' (adjust manually if needed).
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS movement_type TEXT NOT NULL DEFAULT 'gasto';

ALTER TABLE transactions
    DROP CONSTRAINT IF EXISTS transactions_movement_type_check;

ALTER TABLE transactions
    ADD CONSTRAINT transactions_movement_type_check
    CHECK (movement_type IN ('ingreso', 'gasto', 'transferencia'));

-- 3. (Optional) speeds up the movement type filter on the transactions page
CREATE INDEX IF NOT EXISTS idx_transactions_movement_type
    ON transactions(movement_type);
