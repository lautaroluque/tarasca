# Portable Agent Workflow Starter

A small repository-level workflow for carrying planning and execution state across OpenCode models and coding harnesses such as Codex and Claude Code.

## Files

- `AGENTS.md` — canonical durable project rules.
- `.agent/PLAN.md` — task-specific intended implementation path and acceptance criteria.
- `.agent/TASK.md` — actual execution state, discoveries, deviations, verification, and handoff context.
- `CLAUDE.md` — thin Claude Code adapter that points back to the canonical portable files.
- `.opencode/commands/plan.md` — research and create an implementation plan using the planning agent.
- `.opencode/commands/implement.md` — execute the active plan.
- `.opencode/commands/checkpoint.md` — refresh durable execution state.
- `.opencode/commands/handoff.md` — prepare state for another model/harness.
- `.opencode/commands/resume.md` — reconcile and resume existing work.

## Mental model

```text
AGENTS.md       What rules always apply?
.agent/PLAN.md  What are we intending to do?
.agent/TASK.md  What has actually happened so far?
Git/repository  What is objectively true right now?
```

The repository wins if any task document becomes stale.

## Typical OpenCode workflow

### 1. Plan

```text
/plan add CSV import support without changing existing JSON behavior
```

The planning agent inspects the repository, writes `.agent/PLAN.md`, and initializes `.agent/TASK.md`. It must not begin implementation.

Review the plan when the task warrants human review.

### 2. Implement

```text
/implement
```

The implementation agent reads the canonical instructions, active plan, task state, and Git state; then executes the plan. It updates plan checkboxes and task state as work progresses.

You can add guidance without replacing the plan silently:

```text
/implement focus on the importer tests first
```

### 3. Checkpoint

```text
/checkpoint
```

Refresh `.agent/TASK.md` from the actual repository state. This is useful before a risky change, a long break, or a model switch.

### 4. Switch models inside OpenCode

Usually no cross-harness handoff is necessary because the OpenCode session retains its context. A checkpoint is still useful as durable state.

### 5. Switch harnesses

```text
/handoff codex
```

or:

```text
/handoff claude
```

This refreshes task state while preserving active plan progress and gives a concise resume instruction for the target harness.

### 6. Return to OpenCode

```text
/resume
```

The agent reads the plan/task state, reconciles them against Git and the repository, and continues the remaining plan.

Optional:

```text
/resume prioritize the failing integration test
```

## Plan authority

An active `.agent/PLAN.md` is authoritative for implementation intent, but it is not immutable.

Agents must not silently deviate. If repository evidence proves a planned step wrong or obsolete, the agent should update the plan and record the reason in `.agent/TASK.md`. Material changes to scope, public behavior, architecture, or acceptance criteria require a decision unless already authorized.

This avoids two bad extremes: agents ignoring plans, and agents blindly implementing a stale plan.

## Cross-harness behavior

OpenCode and Codex can consume `AGENTS.md` as project guidance. `CLAUDE.md` is intentionally a thin Claude Code adapter that tells Claude to use the same canonical instructions and task artifacts.

The portable handoff is therefore the repository itself plus:

```text
AGENTS.md
.agent/PLAN.md
.agent/TASK.md
git status / diff
verification results
```

No harness-specific chat transcript is required to be the source of truth.

## Git policy for task artifacts

A reasonable default is to commit the reusable workflow (`AGENTS.md`, `CLAUDE.md`, `.opencode/commands/`) and keep `.agent/TASK.md` local.

Whether to commit `.agent/PLAN.md` is a team/project choice. Committing it is useful when plans are reviewed or shared; ignoring it is reasonable for personal ephemeral planning. See `gitignore-snippet.txt`.

## Customize first

Before using this on a real repository, edit `AGENTS.md` with the project's runtime, package manager, repository structure, commands, architecture constraints, and verification requirements.

The templates deliberately avoid automatic provider switching or launching another harness. Provider choice can have cost and privacy implications, especially for client code.
