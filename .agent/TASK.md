# Task State: Personal Financial Tracker

## Goal

Build a personal financial tracker/planning app (Streamlit + Supabase) that ingests bank/credit card extracts (Excel, PDF), categorizes transactions, and provides dashboards. UI in Spanish. Multi-currency (ARS/USD/USDT...).

## Status

**Phases 1–8 complete (deployed). Post-deployment fixes round: import button fix, PDF parser rewrite, movement types.**

## Completed

- Phase 1: Project scaffolding (pyproject.toml, directory structure, .streamlit config, .gitignore)
- Phase 2: Data layer (models, database CRUD operations)
- Phase 3: Ingestion engine (Excel/CSV/PDF parsing, Fiwind + Galicia Mastercard templates)
- Phase 4: Categorization engine (Spanish keywords, 10 default categories)
- Phase 5: Upload & Transactions pages (file upload, preview, import, filtering, inline editing)
- Phase 6: Dashboard & Budgets pages (Plotly charts, currency switcher, budget tracking)
- Phase 7: Integration & polish (navigation, tests, lint, typecheck)
- Phase 8: Deployment (done by user: Streamlit Community Cloud + Supabase)

## Post-deployment fixes (current round)

1. **Import button never executed** → `src/pages/upload.py` rewritten to persist
   parsed transactions in `st.session_state`; preview/import render outside the
   button block; state invalidated on file/template change, cleared after import.
2. **Currency check constraint violation (USDT)** → schema no longer restricts
   currencies. Migration: `supabase_migration_002_movement_types.sql`
   (drops `transactions_currency_check`, adds `movement_type`).
3. **Galicia PDF duplicated rows + dropped rows** → `parse_pdf` rewritten as a
   positional parser (`extract_words` + x-coordinates vs. PESOS/DÓLARES header):
   - amounts inside descriptions (e.g. `(USA,USD, 7,29)`) no longer produce
     phantom ARS/USD duplicate rows
   - Spanish month abbreviations (Ago, Dic...) parsed manually — locale-independent
     (`parse_spanish_date`); previously ALL "Ago" rows were silently dropped
     (45 rows → 68 rows on the sample)
4. **Movement concepts** → new `src/core/movements.py`:
   - `movement_type`: `ingreso` | `gasto` | `transferencia` on every transaction
   - sign convention: positive = money in, negative = money out
   - Galicia: purchases = gasto, negative detail amounts (refunds) = ingreso,
     `SU PAGO` = transferencia
   - Fiwind: `Ganancia/Rendimiento` = ingreso, `Retiro a <persona>` = gasto,
     `Conversión` = transferencia and emits **both sides** (ARS +, USDT −) so
     per-currency balances stay consistent
   - UI: type filter + inline type editor on Transacciones; dashboard metrics/
     charts split by type; budgets count only `gasto`
   - **User confirmed both classification assumptions** (Retiro a persona = gasto;
     Conversión Monto = money in, Monto Origen = money out)
5. **Import dedupe** → `src/pages/upload.py::_dedupe_key` compares incoming rows
   against existing DB rows over the batch date range on
   (date UTC-naive, description, amount, currency, account, comprobante);
   already-imported rows are skipped and reported ("X ya existían y se omitieron")
6. **Post-deploy round 2 (silent import / invisible records)**:
   - `st.rerun()` after import wiped the success message → flash messages now
     stored in `st.session_state["import_flash"]` and rendered on next run
   - default date filters hid imported Aug/Sep data (transactions page defaulted
     to current month, dashboard to current month) → transactions filter defaults
     to no range; dashboard defaults to the month of the latest transaction
   - `nlargest` on string dates crashed dashboard → dates normalized to
     datetime64 when building the DataFrame (commit 39e1f66)
   - **DB cleanup executed** (user approved): 91 legacy rows from old-parser
     imports deleted, 2 missing Fiwind rows backfilled → table now has exactly
     74 correct rows (68 Galicia + 6 Fiwind), 0 duplicate keys, 0 sign issues.
     Tools: `scripts/cleanup_imports.py` (idempotent, dry-run by default),
     `scripts/verify_db.py` (read-only sanity check)

## Verification Results

- Tests: 28 passed (`uv run pytest`)
- Lint (ruff): all checks passed (src/, tests/, scripts/)
- Typecheck (mypy): no issues in 15 source files
- DB verified: 74 rows, 0 duplicates, 0 sign inconsistencies

## Key Discoveries

- Fiwind: Excel sheets "Actividad"/"Balance"; date `%d/%m/%Y %H:%M:%S`;
  multi-currency rows (ARS, USDT); conversion rows carry Monto/Monto Origen/Precio
- Galicia Mastercard: 8-page PDF; tables identified by `PESOS`/`DÓLARES` header
  words; amount columns separated by x-position (right-aligned ~x=500 ARS,
  ~x=580 USD); `SU PAGO` rows only appear in the CONSOLIDADO section of page 1;
  statement negative = refund (detail) or payment (summary)
- Flexible metadata model required for bank-specific fields (Tipo, Comprobante, etc.)
- Supabase new key naming: `publishable_key` / `secret_key` (also reads env vars
  `SUPABASE_URL` / `SUPABASE_SECRET_KEY` for local runs)

## Deviations

- Relaxed mypy strict mode (check_untyped_defs = false, disallow_untyped_defs = false)
- type: ignore comments for SQLModel JSONB metadata field
- budgets `currency` still CHECK (ARS, USD) — crypto budgets not needed yet

## Next Steps

1. Push latest commits and let Streamlit Community Cloud redeploy
2. User testing on mobile/tablet; import another statement period when available
