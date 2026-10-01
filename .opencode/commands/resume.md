---
description: Resume work from the portable task handoff
---

Resume the task described in `.agent/TASK.md`.

Before making changes:

1. Read `AGENTS.md`, `.agent/PLAN.md` if it contains an active plan, and `.agent/TASK.md`.
2. Inspect `git status` and the relevant current diff.
3. Inspect the files referenced by the handoff.
4. Reconcile `.agent/TASK.md` against the actual repository state. The repository wins if they disagree.
5. If verification commands are cheap and safe, rerun the narrowest relevant check to confirm the current state.

Then continue from the recommended next step. If an active plan exists, follow its remaining steps and acceptance criteria. Do not silently deviate; update the plan and record the rationale in `.agent/TASK.md` when repository evidence requires a change.

Do not:

- discard existing user/agent changes,
- reset or rebase,
- commit or push unless explicitly asked,
- repeat failed approaches documented in `.agent/TASK.md` unless new evidence justifies retrying them.

If `$ARGUMENTS` is non-empty, treat it as additional resume guidance or a changed priority:

`$ARGUMENTS`

When you reach a meaningful checkpoint, update `.agent/TASK.md` so it remains usable for another handoff.
