---
description: Prepare a durable handoff to another model or coding harness
---

Prepare the current task for handoff. The requested target is: `$ARGUMENTS`.

First perform the same checkpointing work as `/checkpoint`: inspect the actual repository state, `git status`, relevant diffs, changed files, and available verification results, inspect `.agent/PLAN.md` when it contains an active plan, then create or refresh `.agent/TASK.md`. Preserve current plan progress and material deviations.

The handoff must preserve only information that will help another agent continue effectively:

- Goal
- Current status
- Decisions and rationale that still matter
- Important discoveries
- Failed/rejected approaches worth remembering
- Files involved and why
- Verification status
- Blockers/unresolved questions
- One recommended next step

Rules:

- `AGENTS.md` is the canonical durable project guidance; do not duplicate it in `.agent/TASK.md`.
- The repository and Git diff are the source of truth.
- Do not invent verification results.
- Do not include secrets, credentials, tokens, or sensitive client data.
- Do not commit, push, reset, rebase, or discard changes.

Then give me a minimal resume instruction for the target harness.

If the target is `codex`, use this shape:

`Read AGENTS.md, .agent/PLAN.md if active, and .agent/TASK.md. Inspect git status and the current diff, reconcile the handoff against the repository, then continue from the recommended next step. Do not discard existing changes.`

If the target is `claude` or `claude-code`, assume `CLAUDE.md` is present and use this shape:

`Read .agent/PLAN.md if active and .agent/TASK.md, inspect git status and the current diff, reconcile the handoff against the repository, then continue from the recommended next step. Do not discard existing changes.`

If the target is another OpenCode model, say that the current OpenCode session already retains conversational context and recommend switching models directly; still keep `.agent/TASK.md` refreshed as a durable checkpoint.

For any other target, produce an equivalent concise instruction using `AGENTS.md`, the active `.agent/PLAN.md` when present, `.agent/TASK.md`, Git state, and verification results.
