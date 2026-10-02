-- Tarasca migration 003: phone uploads via Supabase Storage
-- Run this in the Supabase SQL Editor if you already created the tables
-- with a previous schema (supabase_schema.sql).

-- 1. Private bucket for files shared from the phone.
--    The Android app uploads here with the publishable (anon) key;
--    the Streamlit app reads with the secret key (bypasses RLS).
INSERT INTO storage.buckets (id, name, public)
VALUES ('imports', 'imports', false)
ON CONFLICT (id) DO NOTHING;

-- 2. RLS on storage.objects must be enabled for policies to take effect.
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- 3. Anyone holding the publishable key may INSERT (upload) files into the
--    imports bucket. No SELECT/DELETE policies for anon → uploaded files
--    cannot be read back through the anon key, only through the secret key.
CREATE POLICY "Phone uploads: anon can insert into imports"
    ON storage.objects
    FOR INSERT
    TO anon
    WITH CHECK (bucket_id = 'imports');

-- 4. (Optional) restrict uploads to statement file types.
--    Uncomment if you want to enforce MIME types at the database level.
-- CREATE POLICY "Phone uploads: anon can insert statement files"
--     ON storage.objects
--     FOR INSERT
--     TO anon
--     WITH CHECK (
--         bucket_id = 'imports'
--         AND (metadata->>'mimetype' IN (
--             'application/pdf',
--             'text/csv',
--             'application/vnd.ms-excel',
--             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
--         ))
--     );
