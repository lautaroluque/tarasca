# Task State: Phone Uploads + Real-Time Card Expenses

## Goal

Two ingestion channels: (1) Android share-sheet → Supabase Storage, (2) card-notification email ingest polled on a GitHub Actions cron, without duplicating rows when statements import.

## Status

Mostly implemented. Gates green: `uv run pytest` 53 passed, `uv run ruff check src/ scripts/ tests/` clean, `uv run mypy src/` clean.

## Done

- Phase 0: `get_supabase_client()` headless fallback (env vars) + `tests/test_database.py`.
- Phone upload: `mobile/` Kotlin app, storage bucket migration, "Desde el teléfono" on Importar.
- Email ingest: `src/core/email_templates.py`, `src/core/email_ingest.py`, `src/core/merging.py`, `scripts/poll_email.py`, `tests/test_email_ingest.py`, `.github/workflows/email-ingest.yml`.
- Android build workflow `.github/workflows/build-android.yml` with `local.properties` written from repo secrets (never committed).

## Open items

- [ ] Live verification of email ingest (PLAN 2.8) — dry-run via `workflow_dispatch`, then real insert.
- [ ] Sideload APK + E2E phone share (PLAN 1.4).
- [ ] README docs (PLAN 3.3).

## Recent fixes (2026-10-06) — CI hangs/failures

Verified facts:

- A wrong IMAP password fails in ~1s with `imaplib.IMAP4.error: [AUTHENTICATIONFAILED]`. It is **not** the cause of a hang; previously it escaped as a raw traceback.
- `import streamlit` alone does not hang or print; the CORS banner comes from `.streamlit/config.toml` (`enableCORS = false`) being read when `st.secrets` is touched.
- `postgrest` already applies a 120s HTTP timeout, so Supabase calls were not the hang.

Changes:

- `src/core/database.py`: never import Streamlit unless it is already in `sys.modules` (and a runtime exists). Headless runs go straight to env vars.
- `src/core/email_ingest.py`: `IMAP_TIMEOUT_SECONDS = 60` on `IMAP4_SSL`; `MAX_MESSAGES_PER_RUN = 500`;
  `INGEST_START_DATE = 2026-08-01` sent as an IMAP `SINCE` criterion (user: no need to ingest emails older than August — statements already cover them), so a first run never walks pre-August history.
- **Root cause of the 6h hang**: first run has `last_uid=0` → `UID 1:*` matched the whole mailbox → sequential full-RFC822 FETCHes with no bound; `set_ingest_state` only runs after the loop, so a killed run never advanced the cursor and the next run restarted from zero.
- `scripts/poll_email.py`: catches `imaplib.IMAP4.error` and `socket.timeout` with a one-line error; all prints flushed.
- `.github/workflows/email-ingest.yml`: `timeout-minutes: 10`, `PYTHONUNBUFFERED: 1`.

Note: if a run is killed before `set_ingest_state`, its batch is reprocessed next run; dedupe via `merge_with_existing` still prevents duplicate rows.

## Next step

Trigger `workflow_dispatch` on email-ingest and read the now-unbuffered output to confirm it completes under 10 minutes.
