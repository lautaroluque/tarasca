---
description: Refresh the portable task checkpoint in .agent/TASK.md
---

Create or refresh `.agent/TASK.md` so another model or coding harness could continue the current task without needing this chat history.

Use the repository state as the source of truth. Inspect the current work before writing the checkpoint, including `git status`, the relevant diff, changed files, `.agent/PLAN.md` when it contains an active plan, and any test/build results available in the session. Do not merely summarize the conversation.

Keep `.agent/TASK.md` concise and factual. It must contain:

- Goal
- Active plan progress and any deviations, when `.agent/PLAN.md` is active
- Current status
- Decisions and rationale that still matter
- Important discoveries about the codebase or problem
- Failed/rejected approaches worth remembering so they are not repeated
- Files involved and why
- Verification status: tests, lint, typecheck, build as applicable
- Blockers or unresolved questions
- One recommended next step

Rules:

- Do not duplicate durable project instructions already present in `AGENTS.md` or the full plan from `.agent/PLAN.md`.
- Do not invent test results. Say `not run` when appropriate.
- Do not include secrets, credentials, tokens, or sensitive client data.
- If `.agent/TASK.md` disagrees with the repository, fix the checkpoint to match the repository.
- Do not commit or push anything.

After updating the file, reply with a short checkpoint summary and the recommended next step.
