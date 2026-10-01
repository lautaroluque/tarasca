# Project Agent Instructions

This file is the canonical, harness-independent source of project instructions.
Keep it concise and update it when project conventions change.

## Project overview

- Purpose: Personal financial tracker/planning app that ingests bank/credit card extracts (CSV, PDF), parses and categorizes transactions automatically, and provides spending dashboards. Accessible via web browser on any device.
- Primary language/runtime: Python 3.13
- Package/dependency manager: uv
- Cloud hosting: Streamlit Community Cloud (free tier)
- Database: Supabase (PostgreSQL, free tier)

## Repository structure

- `src/app.py`: Main Streamlit application entry point
- `src/pages/`: Multi-page Streamlit views (Dashboard, Upload, Transactions, Budgets)
- `src/core/`: Business logic modules
  - `src/core/ingestion.py`: File parsing (CSV, PDF) and bank template mapping
  - `src/core/categorization.py`: Rule-based and ML-based transaction categorization
  - `src/core/database.py`: Supabase/PostgreSQL connection and CRUD operations
- `src/components/`: Reusable Streamlit UI components
- `tests/`: Unit and integration tests
- `.streamlit/`: Streamlit configuration (theme, secrets)
- `pyproject.toml`: Project metadata and dependencies

## Common commands

- Install/setup: `uv sync`
- Run locally: `uv run streamlit run src/app.py`
- Focused tests: `uv run pytest tests/test_<module>.py`
- Full tests: `uv run pytest`
- Lint: `uv run ruff check src/`
- Typecheck: `uv run mypy src/`
- Build: N/A (interpreted language, no build step)

## Engineering rules

- Prefer the smallest change that fully solves the task.
- Follow existing project patterns before introducing new abstractions.
- Do not add dependencies unless they provide clear value.
- Do not modify generated files directly unless the project explicitly requires it.
- Do not commit secrets, credentials, tokens, private keys, or client data.
- Preserve backward compatibility unless the task explicitly requires a breaking change.

## Verification

Before considering implementation work complete:

1. Run the narrowest relevant tests first.
2. Run the project's normal lint/typecheck/build checks when applicable.
3. Inspect the final diff for unintended changes.
4. Report any verification step that could not be run and why.

## Git behavior

- Do not commit, push, rebase, reset, or force-update branches unless explicitly asked.
- Never discard user changes that you did not create.
- Treat the working tree as shared state across coding harnesses.

## Portable task state

For non-trivial work, use `.agent/TASK.md` as the current-task handoff document.

- `AGENTS.md` contains durable project knowledge.
- `.agent/TASK.md` contains temporary task state.
- The repository and Git diff are the source of truth; reconcile `.agent/TASK.md` against them if they disagree.
- Keep `.agent/TASK.md` concise enough for another model or harness to read quickly.

## Implementation plans

For non-trivial implementation work, `.agent/PLAN.md` is the authoritative execution plan when it contains an active task plan.

Before modifying code:

1. Check whether `.agent/PLAN.md` contains an active plan rather than the untouched template.
2. If active, read it completely and use it to guide implementation.
3. Follow the plan in order when practical and keep its checkboxes/status current as work progresses.
4. Do not silently deviate from the plan.
5. If repository evidence shows a planned step is incorrect, unsafe, obsolete, or impossible, preserve the plan's goal and constraints, update the plan as needed, and record the deviation and rationale in `.agent/TASK.md`.
6. If a required deviation materially changes scope, public behavior, architecture, or acceptance criteria, stop and request a decision unless the user already authorized that class of change.
7. Before declaring the task complete, verify every applicable acceptance criterion in the plan.

Task artifacts have distinct roles:

- `AGENTS.md`: durable project rules and conventions.
- `.agent/PLAN.md`: intended implementation path and acceptance criteria.
- `.agent/TASK.md`: actual execution state, discoveries, deviations, and handoff context.
- Repository/Git state: objective source of truth when any task artifact is stale.
