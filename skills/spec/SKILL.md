---
name: spec
description: >-
  Spec-driven development in the active repository's spec/{feature}/ directory.
  Use when the user says /spec, "write a spec", "plan a feature", "create a PRD",
  "spec status", or references a spec/ directory. Determines intent from context —
  no subcommands. Spec turns write only under spec/{feature}/ unless the user
  explicitly approves implementation.
license: MIT
metadata:
  audience: software engineers
  tools: filesystem,git
---

# Spec-Driven Development

Manage feature specs in `spec/{feature-name}/`. Each feature gets its own directory
with lean, focused documents.

Resolve the active repository from the current working directory, then use its
repo-root `spec/` path. Prefer kebab-case feature names. Prefix with a component
or area when that improves discoverability (e.g. `api-rate-limits`,
`checkout-retry`). Use `shared-*` or `platform-*` only for genuinely cross-cutting
work.

Keep active specs under `spec/`. If the repository has `spec-archive/`, read
archived material for context but ask before reactivating it. Follow any
repository-local agent instructions (`AGENTS.md`, `CLAUDE.md`, etc.) for naming,
archive policy, and production boundaries.

## Spec-only boundary

When the user invokes this skill with `/spec`, `$spec`, "write a spec",
"create a spec", "spec this out", "plan this", or similar wording, they are asking
for **specification work only**.

During a spec turn:

- Do **not** implement application code.
- Do **not** edit source/config outside `spec/{feature-name}/`.
- Do **not** create migrations outside `spec/{feature-name}/sql-runbook.md`
  (draft SQL lives in the runbook until implementation is approved).
- Do **not** run formatters or refactors that modify application source.
- Do **not** "just make the obvious fix" after research confirms the approach.

Allowed work:

- Reading/searching code and docs for context.
- Running **read-only** investigation when the user asks or the spec needs facts.
- Writing/updating artifacts under `spec/{feature-name}/`.

Do not write `GOAL.md` during initial speccing unless the user explicitly asks.
`GOAL.md` is a later handoff artifact after the user has reviewed and accepted the
spec (especially `mockups.md`).

After the spec, plan, or findings are written, **stop** and ask for explicit
implementation approval or review. Implementation may only begin later when the
user clearly says to build, implement, apply, code, or otherwise approve code
changes.

## How it works

The user mentions a spec naturally — determine intent from context:

- If `spec/{name}/` doesn't exist → create it (new spec)
- If `spec/{name}/progress.md` exists → read it, continue from where you are
- If only `spec-archive/{name}/` exists → read for context; ask before reactivating;
  do not edit archived specs in place
- Always check first: does the directory exist? What files are in it? Status?

## File persistence rule

**Every operation MUST write its output files to disk before completing.**

- Generating content in the conversation is not enough — save with the Write tool
  to `spec/{name}/`
- After writing each file, verify it exists (`ls -la spec/{name}/` or equivalent)
- Never consider work complete until required output files are on disk
- If work is interrupted, files on disk are the only thing that survives

### Required output files

| Activity | MUST write to disk | Also write if applicable |
|----------|-------------------|--------------------------|
| New spec | `SPEC.md`, `mockups.md`, `progress.md` | `findings.md` (large specs) |
| New spec (SQL / schema changes) | `sql-runbook.md` | — |
| Planning | `plan.md`, update `progress.md` | Update `mockups.md` if design changes |
| Goal handoff (only when asked) | `GOAL.md`, update `progress.md` | — |
| Implementing | Update `progress.md` after each step | Keep `mockups.md` current |
| Resuming | Update `progress.md` with recovery entry | — |

**Write early, write often.** Don't accumulate content in conversation and write
only at the end.

## Diagram rule

Every spec MUST include `spec/{name}/mockups.md`.

- Always include system / workflow / sequence / state views that explain the
  feature end to end — even for backend-only work.
- If there is user-facing UI, also include wireframes or interaction flows.
- ASCII, Mermaid, markdown tables, or annotated wireframes are all fine; they must
  be concrete enough for the user to validate quickly.
- A spec is not complete until `mockups.md` exists and matches the current spec.
- Treat `mockups.md` as a **review gate** — expect iteration before coding.

## ELI10 rule

Every `SPEC.md` MUST include an `## ELI10` section immediately after the title and
before `## Summary`.

- Plain language, short sentences, no unexplained jargon.
- What is changing, why it matters, safest next step, what is **not** happening yet.
- One short paragraph or 3–6 bullets.
- Update whenever scope, phase boundaries, or next action changes.

## Recovery block

Every `progress.md` MUST include the **verbatim** recovery block from
[templates/progress.md](templates/progress.md) at the top. Never omit or paraphrase
it. Copy it exactly.

## Link each file individually

When telling the user which files you wrote or updated, always list **individual
file paths**. Never point at the folder only.

Desktop clients turn relative file paths into clickable previews; folder paths often
cannot be opened the same way.

```
Files written:
- `spec/feature-name/SPEC.md`
- `spec/feature-name/mockups.md`
- `spec/feature-name/plan.md`
- `spec/feature-name/progress.md`
```

Apply this after every create/update/status summary.

## Determining intent

Do **not** require subcommand syntax. Parse meaning from context:

| User says something like… | What to do |
|---|---|
| "spec out X", "write a spec for X", "create a PRD for X" | Create `spec/{name}/`, write SPEC.md collaboratively |
| "plan the implementation for X", "plan X" | Read SPEC.md, explore codebase, write plan.md |
| "let's build X", "implement X", "start building X" | Read all spec files, continue from Next Action |
| "where are we on X", "spec status", `/spec` | Read progress.md, show status |
| "write the goal", "GOAL.md", "handoff for implementation" | Write `GOAL.md` only after accepted spec |
| Any mention of an existing spec name | Read progress.md first |

When ambiguous, read `progress.md` and decide from the current phase.

## Adaptive sizing

Tell the user what size you picked and why.

### Small

**Signals:** "fix", "update", "tweak", "rename", "config change", description under
~3 sentences, single-file change  
**Files:** `SPEC.md` + `mockups.md` + `progress.md`  
**Example:** "Fix the empty-state message on the settings page."

### Medium

**Signals:** "add", "create", "implement", "build", roughly 2–5 files, sequenced steps  
**Files:** above + `plan.md`  
**Example:** "Add webhook retries with exponential backoff and a dead-letter view."

### Large

**Signals:** "evaluate", "research", "migrate", "redesign", "investigate", 5+ files,
unknowns  
**Files:** above + `findings.md`  
**Example:** "Migrate session storage from sticky servers to a shared cache."

**Override:** The user can request a different size. Small can promote to medium later.

## What to do

### Starting a new spec

1. **Validate name.** Kebab-case; optional area prefix; ensure `spec/{name}/` is free.
2. **Create directory:** `mkdir -p spec/{name}/`
3. **Determine size.** Tell the user: "This looks like a **{size}** spec — I'll create {files}."
4. **Explore the codebase** for context:
   - Read `AGENTS.md` / `CLAUDE.md` / project docs if present
   - Glob/Grep for related source, patterns, similar features
5. **Write `SPEC.md` collaboratively** using [templates/spec.md](templates/spec.md).
   Include `## ELI10`. Draft sections, ask targeted questions. Do **not** dump a full auto-spec.
   - **SAVE:** `spec/{name}/SPEC.md`
6. **Write `mockups.md`** using [templates/mockups.md](templates/mockups.md).
   System/workflow view always; UI views when relevant. Present for review.
   - **SAVE:** `spec/{name}/mockups.md`
7. **Write `progress.md`** with status `speccing`, today's date, session log, and recovery block.
   - **SAVE:** `spec/{name}/progress.md`
8. **Write `findings.md`** for large specs (research from step 4).
   - **SAVE:** `spec/{name}/findings.md`
9. **Write `sql-runbook.md`** if the work involves schema / SQL migrations (see below).
10. **Verify:** list `spec/{name}/`

### Creating a plan

1. Read `SPEC.md` and `progress.md`.
2. Explore implementation surface (patterns, files to touch, tests).
3. Write `plan.md` from [templates/plan.md](templates/plan.md). Each step: specific files + verification.
4. Refresh `mockups.md` if exploration changed system shape or UI.
5. Update `progress.md` → status `planned`.
6. Verify files on disk.

### Creating GOAL.md (handoff)

Only when the user explicitly asks for a goal / handoff / execution contract after
reviewing the spec.

1. Read `SPEC.md`, `mockups.md`, `plan.md`, `findings.md`, `progress.md`.
2. Do not invent new scope.
3. Write `GOAL.md` with:
   - Objective
   - Scope (in / out)
   - Source of truth (links to the other spec files)
   - Ordered execution steps with verification
   - Acceptance criteria
   - Risks / blockers
   - Recovery notes (where to resume after compaction)
4. Update `progress.md` → status `goal-ready`.
5. Stop for user review. Do not implement until explicit approval.

### SQL / schema changes

If the work involves schema, procedures, views, or seed/backfill SQL, write
`spec/{name}/sql-runbook.md` during the **spec** phase.

The runbook holds the **draft** migration plus verification and rollback. During
**implementation** (after approval only):

1. Create the real migration file in whatever path **this repository** uses
   (discover from existing migrations; do not invent a foreign project path).
2. Run against the **development** environment first.
3. Never touch production unless the user explicitly asks.

#### sql-runbook.md shape

Use this outline (fill in repo-specific paths when implementing):

- Title: `sql-runbook.md — {Spec Name}`
- **Migration file (create during implementation):** `{repo-migration-path}/{NNN}_{Name}.sql`
- **Target environments:** dev → staging → prod (adjust to this repo)
- **Deploy order:** document the repo's actual order
- **Migration Script** — full SQL with idempotent guards where possible
- **Step-by-step reference** — same SQL broken into logical steps, each with a verify query and expected result
- **Rollback** — statements to undo
- **Summary table** — `# | Change | Object | Action`

Rules:

- Full SQL only (no stubs for procedures).
- Idempotent where the platform allows.
- Every step has a verification query with an expected result.
- Rollback section required.
- Dev first.

### Implementing

Only after explicit user approval to implement.

1. Read all spec files (including `GOAL.md` if present).
2. Summarize: status, last completed step, next action.
3. Follow `plan.md` steps when present; else work from acceptance criteria.
4. Keep `mockups.md` current if architecture/workflow/UI changes.
5. Update `progress.md` after **every** step.
6. When done, set status to `done`.

### Checking status

**General:** Scan active `spec/*/progress.md` (skip `spec-archive/` unless asked):

| Spec | Status | Current Step | Next Action |
|------|--------|--------------|-------------|

**Specific:** Show that spec's `progress.md` (and link the other files).

## Progress update rules

- After each plan step → update Current Step, Next Action, session log
- Decisions → Decisions table (rationale + date)
- Blockers → Blockers list
- Errors → Errors table
- Architecture / workflow / UI change → update `mockups.md`
- Before ending a session → latest session log entry has a **"Next:"** line

The **"Next:"** line is the most important field for cross-session recovery.

## Behavioral rules

### Core philosophy

**Context window = RAM (volatile). Filesystem = disk (persistent).**

Anything important gets written to disk.

### 2-Action rule

After every 2 search/browse/explore operations, save findings to `findings.md`.

### Read before decide

Re-read `plan.md` + `progress.md` before major decisions. Don't rely on memory alone.

### 3-Strike error protocol

| Attempt | Action |
|---------|--------|
| 1 | Diagnose and fix |
| 2 | Alternative approach (never repeat the same failing action) |
| 3 | Broader rethink |
| After 3 | Escalate to user; log attempts in `progress.md` Errors |

### 6-Question reboot test

| Question | Source |
|---|---|
| Where am I? | Current Step in `progress.md` |
| Where am I going? | Remaining steps in `plan.md` |
| What's the goal? | Summary / ELI10 in `SPEC.md` |
| What does it look like? | `mockups.md` |
| What have I learned? | `findings.md` |
| What have I done? | Session Log in `progress.md` |

### Context compaction recovery

After `/clear` or compaction:

1. Read `progress.md` (header + recovery block)
2. Read `SPEC.md`, `mockups.md`, `plan.md` / `findings.md` / `GOAL.md` as present
3. `git diff --stat` and `git log --oneline -5` when in a git repo
4. Run the 6-Question reboot test
5. Present recovery summary; continue from Next Action

### Anti-patterns

| Don't | Do instead |
|---|---|
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log to `progress.md` Errors |
| Start implementing without reading | Read spec files first |
| Implement during a pure `/spec` turn | Spec artifacts only until approval |
| Repeat failed actions | 3-Strike rule |
| Keep research only in chat | 2-Action rule → disk |
| Leave diagrams implicit | Keep `mockups.md` concrete and current |
| Skip progress updates | Update after every step |
| Continue from memory after compaction | Full recovery protocol |
| Auto-dump a complete spec | Write collaboratively |
| Hardcode another repo's migration paths | Discover this repo's conventions |
