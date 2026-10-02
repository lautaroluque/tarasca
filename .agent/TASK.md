# Task State: Phone Uploads + Real-Time Card Expenses

## Goal

Add two ingestion channels to Tarasca: (1) share statement files from Android's share sheet into the app, (2) ingest credit-card-use notification emails automatically (~5 min polling) for near-real-time expense tracking, without duplicating rows when monthly statements are imported.

## Status

**Planned; implementation not started.** Plan written to `C:\Users\lauta\.opencode\plan\PLAN.md` (plan-mode constraint: plan files live there, not in `.agent/`).

## Planning discoveries (verified)

- `src/core/database.py::get_supabase_client()` is **broken for CI**: catches only `(ImportError, KeyError)`, but `st.secrets` raises `StreamlitSecretNotFoundError` when no secrets file exists → env-var fallback unreachable. Verified empirically (crashes even with env vars set). Fix first (Phase 0).
- Streamlit Community Cloud sleeps apps after 12h without traffic → email poller must run outside the app → **GitHub Actions cron** (repo is public → free unlimited runners; min interval 5 min; offset minutes to avoid top-of-hour delays).
- PWA share_target route rejected: open Chrome 153 regression drops shared files to installed PWAs + Streamlit can't inject `<link rel="manifest">` in head → **sideloaded Android app** is the primary phone path.
- Supabase free tier: 1 GB storage / 50 MB per file / 500 MB DB; free projects pause after 1 week of inactivity (poller traffic should count as activity — verify early).
- Storage security: private `imports` bucket, INSERT-only RLS policy for `anon` role; publishable key in APK can only add files, never read; app server uses secret key for list/download.
- Repo is public → test fixtures must be synthetic/sanitized; `samples/` and `.streamlit/secrets.toml` already gitignored.
- Existing patterns to reuse: `parse_file`/`classify_movement`/`categorize_transaction` for both new paths; `scripts/` entrypoints; `supabase_migration_NNN.sql` + `supabase_schema.sql` dual files.
- Cross-source merge (email ↔ statement) is the riskiest logic: signature = (account, currency, abs(amount)) + date ±3 days, count-based pairing, description token guard; used by both import directions.

## Recommended first implementation step

Phase 0: fix `get_supabase_client()` env fallback in `src/core/database.py` (broaden except clause) + add a regression test. Small, unblocks everything headless. In parallel, user provides 2–3 sample notification `.eml` files into `samples/emails/` (needed before Phase 2 parser work).

## Open decisions (user input needed)

1. **Phone upload approach**: sideloaded Android app (recommended) vs email relay vs PWA attempt.
2. **Mailbox**: where do card-use notifications arrive (Gmail IMAP + app password vs other IMAP)?
3. **Merge behavior**: skip statement rows that match email rows (v1, recommended) vs also backfill `comprobante` metadata.
