---
description: Execute the active portable implementation plan
---

Implement the active plan in `.agent/PLAN.md`.

Before modifying code:

1. Read `AGENTS.md`, `.agent/PLAN.md`, and `.agent/TASK.md` if present.
2. Inspect `git status`, the relevant diff, and the files referenced by the plan.
3. Reconcile the task documents against the actual repository state. The repository wins if they disagree.
4. Confirm that `.agent/PLAN.md` contains an active plan. If it is missing or still only the template, do not invent a plan here; report that `/plan <task>` should be run first.

Then execute the plan incrementally.

- Follow the plan and preserve its goal, scope, constraints, and acceptance criteria.
- Mark implementation and verification checkboxes as they are actually completed.
- Keep `.agent/TASK.md` synchronized at meaningful milestones, especially discoveries, failed approaches, verification results, blockers, and deviations.
- Never silently deviate. If repository evidence requires a change to the plan, update `.agent/PLAN.md` and record the reason in `.agent/TASK.md`.
- If a deviation materially changes scope, public behavior, architecture, or acceptance criteria and has not already been authorized, stop and request a decision.
- Run the narrowest relevant verification first, then broader checks required by the plan and `AGENTS.md`.
- Do not mark acceptance criteria complete without evidence.
- Do not commit or push unless explicitly asked.

If `$ARGUMENTS` is non-empty, treat it as additional implementation guidance that may refine priorities but does not silently override the plan's constraints:

`$ARGUMENTS`

Before finishing, inspect the final diff, update `.agent/TASK.md`, and report plan completion, verification status, remaining risks, and any incomplete acceptance criteria.
