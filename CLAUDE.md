# Claude Code Adapter

This repository keeps canonical, harness-independent agent instructions in `AGENTS.md`.

At the start of work:

1. Read and follow `AGENTS.md`.
2. If `.agent/PLAN.md` contains an active task plan rather than the untouched template, read it completely and treat it as the authoritative implementation plan.
3. If `.agent/TASK.md` exists, read it for current execution/handoff state.
4. Inspect the actual repository and Git state; they are the objective source of truth if task documents are stale.

When an active plan exists, follow its remaining steps and acceptance criteria. Do not silently deviate. If repository evidence requires a change, preserve the goal/constraints, update `.agent/PLAN.md`, and record the rationale in `.agent/TASK.md`. Request a decision before any unauthorized material change to scope, public behavior, architecture, or acceptance criteria.

Keep project-wide rules in `AGENTS.md`; do not duplicate them here. Keep planning intent in `.agent/PLAN.md` and execution/handoff state in `.agent/TASK.md`.

Before considering implementation complete, follow the verification rules in `AGENTS.md` and verify every applicable acceptance criterion in the active plan.
