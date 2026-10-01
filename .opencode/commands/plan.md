---
description: Research the repository and create an implementation plan without changing application code
agent: plan
---

Plan this task:

`$ARGUMENTS`

Do not modify application/source code. You may inspect files, search the repository, inspect Git state, and run read-only or non-mutating diagnostic commands needed to understand the task.

Read `AGENTS.md` first. Inspect the relevant architecture and existing patterns before planning; do not produce a generic plan from the prompt alone.

Create or replace `.agent/PLAN.md` with a concise, implementation-ready plan containing:

- Goal
- Scope: in scope and out of scope
- Constraints
- Relevant architecture/files and why they matter
- Ordered implementation steps with checkboxes
- Verification/testing strategy with checkboxes
- Risks, assumptions, and unresolved unknowns
- Observable acceptance criteria with checkboxes

Also initialize or refresh `.agent/TASK.md` with the task goal, status `Planned; implementation not started`, important planning discoveries, and the recommended first implementation step. Do not duplicate durable rules from `AGENTS.md`.

Planning rules:

- Prefer existing project patterns over new abstractions.
- Resolve uncertainty by inspecting the repository where practical.
- Clearly identify assumptions that could materially change the implementation.
- Do not claim tests/checks were run unless they actually were.
- Do not commit, push, reset, rebase, or discard changes.
- Do not begin implementation.

Finish with a short summary of the plan and any decision that genuinely requires user input before implementation.
