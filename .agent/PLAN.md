# Implementation Plan: Phone Uploads + Real-Time Card Expenses

> **Status 2026-10-06**: Phases 0–2 are implemented and pushed; the boxes below
> were not ticked retroactively (this plan predates the current task and its
> live state lives in `.agent/TASK.md`). Still open: PLAN 1.4 (sideload APK
> E2E), 1.5, phase 3 (README), and the first real notification email landing as
> a row. PLAN 2.8 verified: a `workflow_dispatch` run on `0253d79` finished in
> 8m11s and wrote `ingest_state` (the 6-hour hang is gone).

## Goal

Add two ingestion channels to Tarasca without changing the existing extract-import flow:

1. **Phone uploads**: share a bank statement file from Android's share sheet directly into the app.
2. **Near-real-time expenses**: ingest credit-card-use notification emails automatically (polled every ~5 min), so daily spending is tracked between monthly statement imports — without duplicating rows when the statement arrives.

## Scope

### In Scope

- Supabase Storage bucket + RLS policies for phone-originated files
- "Desde el teléfono" section on the Importar page (list → download → existing preview/import pipeline)
- Sideloaded Android app (Kotlin, single activity) as the share-sheet sender → Supabase Storage
- Email ingestion pipeline: IMAP polling, per-sender email templates, parser, normalizer
- Cross-source merge/dedupe between email rows and statement rows (both directions)
- `source` column + `ingest_state` table (migration 003) + schema file update
- GitHub Actions scheduled workflow (cron) as the always-on executor
- Unit tests with synthetic fixtures; dry-run modes; README updates

### Out of Scope

- PWA / Web Share Target route (rejected — see Risks)
- Gmail API / OAuth (IMAP + app password is sufficient)
- Telegram bot / other relays (not chosen)
- Enrichment of email rows with statement `comrobante` (optional later)
- iOS support
- Real-time push to the browser (polling latency is acceptable)

## Constraints

- Free tiers only: Streamlit Community Cloud + Supabase (1 GB storage, 50 MB/file, 500 MB DB)
- Repo is **public** → no real bank data or emails in the repo; test fixtures must be synthetic/sanitized
- Python 3.13, uv, ruff/mypy/pytest gates must stay green
- Existing patterns: `src/core/` logic, `scripts/` entrypoints, `supabase_migration_NNN.sql` + `supabase_schema.sql` dual files, `samples/` gitignored
- No new dependencies unless clear value (only `beautifulsoup4` added, for HTML email parsing)
- Secrets only in GitHub Actions secrets / Streamlit secrets / env vars — never committed

## Relevant architecture/files

| File | Why it matters |
|---|---|
| `src/core/database.py` | `get_supabase_client()` catches only `(ImportError, KeyError)`; `st.secrets` raises `StreamlitSecretNotFoundError` when no secrets file exists → **env-var fallback is unreachable in CI (verified)**. Must broaden the except before any headless use. |
| `src/core/ingestion.py` | `parse_file()` + `classify_movement()` — the phone-upload path reuses this unchanged; email rows reuse `classify_movement` for `movement_type`. |
| `src/core/templates.py` | `BankTemplate` pattern — mirror it with an `EmailTemplate` dataclass (sender/subject regex + field extraction). |
| `src/pages/upload.py` | Preview/import pipeline (`_parse_and_store`, `_render_preview`, `_import_transactions`, `_dedupe_key`). Phone files feed this; merge logic extends `_import_transactions`. |
| `src/core/categorization.py` | `categorize_transaction()` reused for email rows. |
| `scripts/` | Entrypoint pattern (`diagnose.py`, `cleanup_imports.py`) → new `scripts/poll_email.py`. |
| `supabase_migration_002_movement_types.sql`, `supabase_schema.sql` | Migration pattern to follow for migration 003. |
| `.streamlit/config.toml` | `server.enableStaticServing` exists (default false) — not needed for the chosen path. |

## Verified research findings (shape the design)

- **Streamlit Community Cloud sleeps apps after 12h without traffic** → an in-app background poller is unreliable; the email poller must run outside the app (GitHub Actions).
- **GitHub Actions: public repos get free unlimited runners**; minimum cron interval is **5 minutes**; schedules can be delayed/dropped at the top of the hour → use offset minutes (e.g. `2-59/5`); schedules auto-disable after 60 days of repo inactivity.
- **Supabase free tier**: 1 GB storage, 50 MB max file, 500 MB DB; **free projects pause after 1 week of inactivity** — the poller's regular DB traffic should count as activity (assumption, verify early).
- **PWA share_target is not viable now**: open Chrome 153 regression drops shared files for installed PWAs, and Streamlit cannot inject `<link rel="manifest">` into the HTML head. → native sideloaded app is the primary path.
- **Storage security model**: private bucket + `INSERT` policy for the `anon` role only (no SELECT/DELETE) → the publishable key embedded in the APK can only add files, never read statements; the app server uses the secret key (bypasses RLS) for list/download.

## Ordered implementation steps

### Phase 0 — Foundation (no user dependency)

- [ ] 0.1 Fix `get_supabase_client()` in `src/core/database.py`: broaden the except to also catch `StreamlitSecretNotFoundError` (or reorder to try env vars first) so headless/CI runs work — **verified broken today**
- [ ] 0.2 Add `beautifulsoup4` to `pyproject.toml` dependencies (HTML email parsing)
- [ ] 0.3 Unit test: `get_supabase_client()` falls back to env vars when no secrets file exists (simulate via temp cwd)

### Phase 1 — Feature 1: phone uploads

- [ ] 1.1 Migration `supabase_migration_003_phone_uploads.sql`: create private `imports` bucket + RLS policy `FOR INSERT TO anon WITH CHECK (bucket_id = 'imports')` (no SELECT/DELETE for anon); mirror into `supabase_schema.sql`
- [ ] 1.2 `src/pages/upload.py`: add source selector ("Subir archivo" / "Desde el teléfono"); phone mode lists bucket objects newest-first via `client.storage.from_("imports").list()`, downloads selected file, feeds existing `_parse_and_store` → shared template select + preview + import (dedupe applies unchanged)
- [ ] 1.3 `mobile/` Android app (Kotlin, single `MainActivity`): `ACTION_SEND` / `ACTION_SEND_MULTIPLE` intent filters (pdf, xlsx, csv, xls); read `content://` URI via `ContentResolver`; HTTP PUT to `https://<ref>.supabase.co/storage/v1/object/imports/<YYYY-MM-DD_HHMMSS>_<name>` with `Authorization: Bearer <publishable key>`, `x-upsert: true`; minimal UI (filename, upload button, result toast)
- [ ] 1.4 Build APK (Gradle), sideload to phone, E2E: share a sample PDF from another app → file appears in Importar phone list → preview → import → visible in Transacciones/Dashboard
- [ ] 1.5 Optional: delete-object button in the phone list (uses secret key)

### Phase 2 — Feature 2: email ingest (gated on user-provided samples)

- [ ] 2.0 **Done (2026-10-02)**: samples received in `samples/emails/` — format documented above
- [ ] 2.1 Migration `supabase_migration_004_email_ingest.sql`: add `source TEXT NOT NULL DEFAULT 'extracto'` to `transactions`; create `ingest_state(key TEXT PK, value TEXT, updated_at)`; mirror into `supabase_schema.sql`
- [ ] 2.2 `src/core/email_templates.py`: `EmailTemplate` dataclass (name, sender regex, subject regex, account, extractor) mirroring `templates.py`; v1 template: sender `alertas@misconsultas.com.ar`, subject `Aviso de consumo con tarjeta`, extractor = BeautifulSoup `li`/`b` field map (Comercio→description, Importe→amount via `parse_amount_argentine`, Moneda PESOS→ARS / DÓLARES→USD, Fecha+Hora→datetime, metadata: tipo, cuotas, estado, tarjeta_ult4, message_id)
- [ ] 2.3 `src/core/email_ingest.py`: IMAP fetch (stdlib `imaplib` + `email`), UID state from `ingest_state`, HTML→text via BeautifulSoup, normalize to transaction dicts (naive Argentina-local datetime, `movement_type` via `classify_movement`, category via `categorize_transaction`, `metadata.message_id` + `source='email'`)
- [ ] 2.4 `src/core/merging.py`: cross-source match — signature `(account, currency, abs(amount))` + calendar date within ±3 days; count-based pairing per group (handles repeated equal amounts); description token-overlap guard; used by **both** directions (statement import skips rows matching existing email rows; poller skips rows matching existing extracto rows)
- [ ] 2.5 Wire merge into `src/pages/upload.py::_import_transactions` (after exact-key dedupe, before insert) and into the poller
- [ ] 2.6 `scripts/poll_email.py`: entrypoint with `--dry-run`; prints per-run report (fetched / new / merged-skipped / inserted); updates `ingest_state`
- [ ] 2.7 `.github/workflows/email-ingest.yml`: `schedule: cron "2-59/5 * * * *"` (offset to avoid top-of-hour load) + `workflow_dispatch`; `astral-sh/setup-uv` with cache; `uv sync --frozen`; env from secrets (`IMAP_HOST`, `IMAP_USER`, `IMAP_APP_PASSWORD`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`)
- [ ] 2.8 Live verification: trigger `workflow_dispatch` with `--dry-run`, review output, enable real insert; confirm a real notification lands as a `gasto` row; import the monthly statement and confirm **no duplicates** (row count unchanged for that period)

### Phase 3 — Polish

- [ ] 3.1 Optional: "Fuente" badge/filter on Transacciones (extracto vs email)
- [ ] 3.2 Optional: "Última ingesta de correos: hace X" on Importar page (reads `ingest_state`)
- [ ] 3.3 README: document phone-upload flow, email ingest architecture, GH Actions setup, secrets list

## Verification / testing strategy

- [ ] Unit: `database.py` env fallback (0.3)
- [ ] Unit: email template parser against synthetic `.eml` fixtures in `tests/fixtures/emails/` (sanitized — repo is public)
- [ ] Unit: merge logic — both directions, equal-amount repeats, email-time vs statement-midnight dates, no false positives for different merchants
- [ ] Unit: poller dry-run with a mocked IMAP mailbox (fixture emails)
- [ ] E2E manual: phone share → import (1.4); email → row → statement import → no dupes (2.8)
- [ ] Gates after each phase: `uv run pytest`, `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/`
- [ ] Idempotency check: run poller twice → second run inserts 0

## Risks, assumptions, unresolved unknowns

### Risks

- **Merge false positives**: two different purchases of the same amount within ±3 days could cross-match → mitigated by count-based pairing + token guard; dry-run review before enabling real inserts
- **GH cron delays/drops** at top of hour → offset minutes; latency bound ~5–15 min (accepted as "almost real time")
- **60-day inactivity auto-disable** of schedules → repo is actively used; note in README
- **Supabase free project pause** after 1 week of inactivity → poller traffic should count as activity; verify in first weeks, add keep-alive if needed
- **Publishable key in APK** is extractable → INSERT-only policy limits damage to bucket pollution (no reads); document accepted risk
- **Chrome 153 share_target regression** → PWA route avoided entirely
- **Public repo** → synthetic fixtures only; `samples/` and secrets stay gitignored (verified in `.gitignore`)

### Assumptions

- Notifications are for **Galicia Mastercard** (account name matches existing rows)
- User can sideload an APK and has Android build tooling (or help setting it up)
- IMAP access to the mailbox (Gmail app password requires 2-Step Verification)
- Every-5-min polling is acceptable latency
- Statement import usually happens after emails, but both orders must work
- Email timestamps converted to naive America/Argentina/Buenos_Aires (consistent with statement rows)

### Resolved (user confirmed 2026-10-02)

- **Phone-upload approach**: sideloaded Android app → Supabase Storage
- **Mailbox**: Gmail, IMAP + App Password (requires 2-Step Verification on the account)
- **Samples received**: `samples/emails/Aviso de consumo con tarjeta.eml` + `... 2.eml` (gitignored)
- **Merge behavior**: v1 = skip statement rows matching email rows (no enrichment)

### Email format (from samples — Galicia Mastercard via MisConsultas)

- From: `alertas@misconsultas.com.ar` · Subject: `Aviso de consumo con tarjeta`
- Date header: `-0300` (Argentina) · Message-ID present (idempotency key)
- HTML body: `<ul>` of `<li>Label: <b>value</b></li>` — parse with BeautifulSoup, split on `:`, take `<b>` text
- Fields: Tipo de Movimiento (COMPRA), Comercio, Importe (Argentine format `38.710,00`), Moneda (PESOS | DÓLARES), Fecha (DD/MM/YYYY), Hora (HH:MM), Cantidad cuotas, Estado (APROBADA), Últimos 4 dígitos (7672), Ubicación
- Both samples are PESOS; DÓLARES → USD mapping is an assumption (no sample yet)

## Observable acceptance criteria

- [ ] Sharing a statement PDF from Android's share sheet makes it appear in Importar → "Desde el teléfono" within seconds; preview + import works; rows visible in Transacciones/Dashboard
- [ ] A card-use notification email produces a `gasto` transaction (correct amount, currency, account, category) within ~15 min of arrival, with no manual action
- [ ] Importing the monthly statement afterwards does **not** create duplicates for email-tracked purchases (verified by row counts)
- [ ] Re-running the poller (or a GH Actions re-run) inserts 0 duplicate rows
- [ ] All existing behavior preserved: 28+ tests pass, ruff/mypy clean, browser upload flow unchanged

---

# Implementation Plan: Combined Balance + Transactions Performance

Added 2026-10-06 (the plan above is the phone-upload/email-ingest task; its live
state is in `TASK.md`). This task came from two user complaints after a large
statement import: Transacciones became unusable, and the dashboard's per-currency
split does not describe a user who earns in USDT and spends in ARS.

## Goal

1. **Transacciones responsive again**: server-side pagination instead of rendering 1000 rows (≈9000 elements, 2004 selectboxes) per run.
2. **Own-account transfers are not expenses**: `Retiro a una cuenta propia` was classified as `gasto` by the `"retiro a"` rule, inflating expense metrics (63% of ARS, 96% of USD "gastos" in the current data).
3. **One combined balance**: a single total across ARS/USD/USDT in a selectable base currency, built from every movement plus user-entered opening balances, converted with rates derived from the user's own swaps.

## Resolved (user confirmed 2026-10-06)

- **Rates**: derived from the user's own swaps (the `monto_origen`/`moneda_origen` metadata on every converted leg) — no external API.
- **Opening balances**: the user enters them per account + currency.
- **Base currency**: selectable switcher, default ARS.
- **Scope of backfill**: only rows matching `cuenta propia` (all 153 are Fiwind); other withdrawals stay expenses.

## Constraints (inherited)

- Supabase PostgREST hard-caps rows per request at 1000 regardless of `limit` → every "give me everything" path must page with `range()` (`get_all_transactions`).
- No schema migration for this task: settings reuse `ingest_state` (the only key/value table) under the key `opening_balances`.
- No new dependencies.

## Steps

- [x] 1.1 `count_transactions()` (PostgREST `count=exact`, unaffected by the row cap) + `get_all_transactions()` in `src/core/database.py`; dedupe/aggregate callers in `upload.py`, `budgets.py`, `poll_email.py` moved off `limit=10000`
- [x] 1.2 `src/pages/transactions.py`: 50 rows/page, page index in `st.session_state`, reset when filters change, pager above and below the list
- [x] 2.1 `src/core/movements.py`: `cuenta propia` → `transferencia` (sign preserved) checked before `retiro a`; tests in `tests/test_movements.py`
- [x] 2.2 Backfill the 153 already-imported rows with `scripts/backfill_own_account_transfers.py`
      — **applied 2026-10-06** (dry-run reviewed first); rollback JSON written to
      `backfill_own_account_rollback.json` (gitignored)
- [x] 3.1 `src/core/fx.py`: rate table pivoted on ARS, median of swaps in the last 60 days, per-currency stale fallback, sample counts/dates exposed for the UI caption
- [x] 3.2 `src/pages/dashboard.py`: "Patrimonio" block (combined total, base-currency switcher, opening-balance editor, rate caption); monthly flows also expressed in the base currency
- [x] 3.3 Settings store `get_setting_json`/`set_setting_json` in `src/core/database.py`; `email_ingest` now delegates to it (no duplicated key/value code)
- [ ] 3.4 User enters the real opening balances in the UI (combined total is negative until then: data starts 2026-01-01)
- [x] 4.1 Delete `.agent/_*.py` scratch scripts before committing
- [x] 4.2 Gates + commit/push (`83b58a3`, pushed together with `0253d79`)

## Acceptance criteria

- [x] Transacciones renders 50 rows/page with "Mostrando 50 de 1579", pager works at both ends of the range, changing a filter returns to page 1 (verified with `AppTest`)
- [x] `Retiro a una cuenta propia` classifies as `transferencia`; after the backfill, expense metrics dropped by 44.47M ARS and 3,692.28 USD (gasto 482 → 329) with every cumulative balance unchanged
- [x] Dashboard shows one combined total in the selected base currency, with a caption naming the swap rates used (verified in ARS and USD)
- [x] Transfers and swaps never appear in the Ingresos/Gastos metrics
- [x] Gates green: `uv run pytest`, `uv run ruff check src/ scripts/ tests/`, `uv run mypy src/`
