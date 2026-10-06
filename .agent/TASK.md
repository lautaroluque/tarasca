# Task State: Combined Balance + Transactions Performance

Current task. The earlier *Phone Uploads + Real-Time Card Expenses* plan still
lives in `.agent/PLAN.md`; its remaining open items are listed at the bottom.

## Goal

1. Transacciones usable again (server-side pagination, 50 rows/page).
2. Own-account transfers are not expenses (classification fix + DB backfill).
3. Dashboard shows one combined ARS/USD/USDT balance in a selectable base
   currency, with opening balances and rates from the user's own swaps.

## Status

**Shipped.** Committed as `83b58a3` and pushed to `origin/main` together with the
email-ingest fix `0253d79`. Gates green (`uv run pytest` 64 passed,
`uv run ruff check src/ scripts/ tests/` clean, `uv run mypy src/` clean).
Verified headless against the real DB and via `AppTest` on both pages.
Backfill applied (see Open items).

## Done

- `src/core/database.py`: `_transaction_query()` shared builder, `count_transactions()`
  (`count=exact`, immune to Supabase's 1000-row cap), `get_all_transactions()`
  (pages with `range()`), `get_setting_json()`/`set_setting_json()`.
- `src/pages/transactions.py`: `PAGE_SIZE = 50`, page index in
  `st.session_state["tx_page"]`, reset when `tx_filter_key` changes, pager top+bottom
  (widget keys suffixed `top`/`bottom`).
- `src/pages/upload.py`, `src/pages/budgets.py`, `scripts/poll_email.py`: replaced
  `limit=10000` with `get_all_transactions()` (the old code silently saw only
  1000 rows, which could let dedupe miss matches → duplicates).
- `src/core/movements.py`: `"cuenta propia"` → `transferencia` (sign-preserving)
  checked before `"retiro a"`.
- `src/core/fx.py`: `collect_rate_samples()` + `build_rate_table()` — ARS pivot,
  median of samples from the last 60 days, per-currency stale fallback,
  `sample_counts`/`newest_sample` for the UI caption.
- `src/pages/dashboard.py`: rewritten — "Patrimonio" (combined total + opening
  balance editor + rate caption) and monthly flows converted to the base currency.
- `src/core/email_ingest.py`: `get_ingest_state`/`set_ingest_state` now delegate to
  the new settings helpers (tests still patch the names on `email_ingest`).
- Tests: `tests/test_fx.py` (new), `tests/test_movements.py` (3 own-account cases),
  `tests/test_database.py` (count + paging).
- `.gitignore`: `backfill_*.json` (rollback files carry transaction ids).

## Open items

- [x] **Backfill applied 2026-10-06**: 153 rows reclassified (all Fiwind:
      ARS 135 rows / -44,473,966.07 · USD 18 rows / -3,692.28). Verified —
      `gasto` 482 → 329, `transferencia` 752 → 905, `ingreso` 345 unchanged,
      every (account, currency) cumulative movement byte-identical, October
      gastos 427,516.50 → 350,000.00 ARS, re-running the script matches 0 rows.
      Rollback file: `backfill_own_account_rollback.json` (gitignored); restore
      with `uv run python scripts/backfill_own_account_transfers.py --rollback FILE`.
- [ ] User enters real opening balances via Dashboard → "Editar saldos iniciales"
      (until then the combined total is negative: -5,260,408.18 ARS, because
      imported data starts 2026-01-01).
- [x] Push verification: on 2026-10-06 a `workflow_dispatch` run of **Email ingest**
      on `0253d79` completed successfully in 8m11s (run 37503414702) and wrote
      `ingest_state.imap_last_uid=51659` — the previous hang is gone. 0 new rows,
      total row count unchanged (1579) → no duplicates. Note: the scheduled run
      earlier that day was on `ae71f3b` (pre-fix) and hit the 10-minute
      `timeout-minutes`; schedules now pick up the fixed code.
- [ ] First real notification email landing as a `gasto` row within ~15 min
      (PLAN 2.8 second half — nothing newer than 2026-08-19 in the mailbox yet).

## Measurements backing the design

- Before: `limit=1000` built ~9,000 elements per run (2,004 selectboxes) and every
  edit replayed it; script time was linear in rows (1000 rows ≈ 7.2 s).
- After: 50 rows → 104 selectboxes; `AppTest` render of both pages is clean;
  pager verified (`Página 2 de 32`, `Mostrando 50 de 1579`).
- Supabase caps every response at 1000 rows: `count_transactions()` reports
  1579, `get_all_transactions()` returns 1579.
- Rates from own swaps (as of 2026-10-06): 1 USDT = 1,584.99 ARS (78 swaps,
  latest 2026-10-01), 1 USD = 1,530.52 ARS (2 swaps, latest 2026-09-04).
- Cumulative movement (no opening balances): Fiwind ARS -1,809,564.06 /
  USDT -1,312.03 / USD 0.00 · Galicia ARS -1,175,867.07 / USD -127.68.

## Earlier task: remaining open items (phone uploads + email ingest)

- [ ] Live verification of email ingest (PLAN 2.8) — `workflow_dispatch` dry-run,
      then a real insert; requires the commit to be pushed first.
- [ ] Sideload APK + E2E phone share (PLAN 1.4).
- [ ] README docs (PLAN phase 3).
