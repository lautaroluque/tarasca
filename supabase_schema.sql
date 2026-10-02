-- Tarasca Database Schema for Supabase
-- Run this in the Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    color TEXT DEFAULT '#808080',
    icon TEXT DEFAULT '📦'
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    description TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,  -- signed: positive = money in, negative = money out
    currency TEXT NOT NULL DEFAULT 'ARS',  -- ARS, USD, USDT, USDC...
    movement_type TEXT NOT NULL DEFAULT 'gasto' CHECK (movement_type IN ('ingreso', 'gasto', 'transferencia')),
    source TEXT NOT NULL DEFAULT 'extracto' CHECK (source IN ('extracto', 'email', 'manual')),
    account TEXT NOT NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Budgets table
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    amount DOUBLE PRECISION NOT NULL,
    currency TEXT NOT NULL DEFAULT 'ARS' CHECK (currency IN ('ARS', 'USD')),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account);
CREATE INDEX IF NOT EXISTS idx_transactions_currency ON transactions(currency);
CREATE INDEX IF NOT EXISTS idx_transactions_source ON transactions(source);
CREATE INDEX IF NOT EXISTS idx_budgets_category_id ON budgets(category_id);
CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year);

-- Ingest state for the email poller (last processed IMAP UID, etc.)
CREATE TABLE IF NOT EXISTS ingest_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default categories
INSERT INTO categories (name, color, icon) VALUES
    ('Vivienda', '#FF6B6B', '🏠'),
    ('Alimentación', '#4ECDC4', '🍽️'),
    ('Transporte', '#45B7D1', '🚗'),
    ('Servicios', '#96CEB4', '💡'),
    ('Entretenimiento', '#FFEAA7', '🎬'),
    ('Salud', '#DDA0DD', '🏥'),
    ('Compras', '#F0E68C', '🛍️'),
    ('Ingresos', '#98D8C8', '💰'),
    ('Transferencias', '#C0C0C0', '🔄'),
    ('Otros', '#808080', '📦')
ON CONFLICT DO NOTHING;

-- Enable Row Level Security (optional, for future multi-user support)
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;

-- RLS Policies (allow all for now, restrict later if needed)
CREATE POLICY "Allow all access to categories" ON categories FOR ALL USING (true);
CREATE POLICY "Allow all access to transactions" ON transactions FOR ALL USING (true);
CREATE POLICY "Allow all access to budgets" ON budgets FOR ALL USING (true);

-- Phone uploads: private Storage bucket for files shared from the phone.
-- The Android app uploads with the publishable (anon) key; the Streamlit
-- app reads with the secret key (bypasses RLS). No SELECT/DELETE policies
-- for anon → files cannot be read back through the anon key.
INSERT INTO storage.buckets (id, name, public)
VALUES ('imports', 'imports', false)
ON CONFLICT (id) DO NOTHING;

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Phone uploads: anon can insert into imports"
    ON storage.objects
    FOR INSERT
    TO anon
    WITH CHECK (bucket_id = 'imports');
