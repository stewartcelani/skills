---
name: spec
description: >-
  Spec-driven development in the active repository's spec/{feature}/ directory.
  Use when user says /spec,
  "write a spec", "plan a feature", "create a PRD", "spec status", or
  references spec/ directory. Determines intent from context — no subcommands.
license: MIT
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Task
---

# Spec-Driven Development

Manage feature specs in `spec/{feature-name}/`. Each feature gets its own directory with lean, focused documents.

Resolve the active repository from the current working directory, then use its repo-root `spec/` path in commands and links. It may be a normal directory or a symlink; inspect the resolved path before editing.

Use a specific kebab-case feature name. Prefix it with the affected component or product when that improves discoverability; use `shared-*` or `platform-*` for genuinely cross-cutting work.

Keep active specs under `spec/`. If the repository has `spec-archive/`, read archived material for context but ask before reactivating it. Follow any repository-local `AGENTS.md` instructions for locations, naming, archive policy, and production boundaries.

## How It Works

The user mentions a spec naturally — the agent determines intent from context:

- If `spec/{name}/` doesn't exist → create it (new spec)
- If `spec/{name}/progress.md` exists → read it, figure out where we are, continue
- If only `spec-archive/{name}/` exists → read it for context and ask whether to reactivate it; do not edit archived specs in place
- Always check first: does the directory exist? What files are in it? What's the status?

## CRITICAL: File Persistence Rule

**Every operation MUST write its output files to disk before completing.** This is non-negotiable.

- Generating spec content in the conversation is NOT enough — it MUST be saved with the Write tool to `spec/{name}/`
- After writing each file, verify it exists: `ls -la spec/{name}/`
- NEVER consider work complete until all required output files are confirmed on disk
- If work is interrupted, the files written so far are the only thing that survives — conversation context is lost between sessions

### Required Output Files

| Activity | MUST write to disk | Also write if applicable |
|----------|-------------------|------------------------|
| New spec | `spec/{name}/SPEC.md`, `spec/{name}/mockups.md`, `spec/{name}/progress.md` | `spec/{name}/findings.md` (large specs) |
| Planning | `spec/{name}/plan.md`, update `spec/{name}/progress.md` | |
| Implementing | Update `spec/{name}/progress.md` after each step | |
| Resuming | Update `spec/{name}/progress.md` with recovery entry | |

**Write early, write often.** If you draft a spec section, write it immediately. Don't accumulate content in conversation and write at the end — if the session ends early, everything unsaved is lost.

## CRITICAL: Diagram Rule

Every spec MUST include `spec/{name}/mockups.md`.

- Always include system diagrams, workflow diagrams, sequence diagrams, state diagrams, or other architecture views that explain how the feature works end to end.
- If the work has any user-facing UI, also include UI diagrams or mockups that show the relevant screens, panels, states, and transitions.
- These can be lightweight ASCII diagrams, Mermaid, markdown tables, or annotated wireframes, but they must be concrete enough that the user can validate the shape of the solution quickly.
- A spec is not complete until `mockups.md` exists on disk and matches the current spec.

## CRITICAL: ELI10 Rule

Every `SPEC.md` MUST include an `## ELI10` section immediately after the title and before
`## Summary`.

- Write it for a smart 10-year-old: plain language, short sentences, and no unexplained internal
  jargon.
- Explain what is changing, why it matters, what the safest next step is, and what is explicitly not
  happening yet.
- Keep it short: one small paragraph or 3-6 bullets.
- Update it whenever scope, phase boundaries, or the next action changes.

## CRITICAL: Recovery Block

Every `progress.md` MUST include the verbatim recovery block from [templates/progress.md](templates/progress.md) at the top. This is the mechanism that ensures the agent re-reads all spec files after context compaction. Never omit it. Never paraphrase it. Copy it exactly.

## Determining Intent

Do NOT require specific subcommand syntax. Parse what the user means from context:

| User says something like... | What to do |
|---|---|
| "spec out X", "write a spec for X", "create a PRD for X" | Create `spec/{name}/`, write SPEC.md collaboratively |
| "plan the implementation for X", "plan X" | Read SPEC.md, explore codebase, write plan.md |
| "let's build X", "implement X", "start building X" | Read all spec files, continue from Next Action |
| "where are we on X", "spec status", `/spec` | Read progress.md, show status |
| Any mention of an existing spec name | Read progress.md first, figure out what's needed |

When ambiguous, read `progress.md` and decide based on what phase the spec is in.

## Adaptive Sizing

Determine size from the user's description. Tell the user what size you picked and why.

### Small
**Signals:** "fix", "update", "tweak", "rename", "config change", description < 3 sentences, single-file change
**Files created:** SPEC.md + mockups.md + progress.md
**Example:** "Fix the 404 page styling" — one file, clear scope, no unknowns.

### Medium
**Signals:** "add", "create", "implement", "build", 2-5 files affected, needs sequenced steps
**Files created:** SPEC.md + mockups.md + plan.md + progress.md
**Example:** "Add webhook retries with exponential backoff" — multiple files (handler, options, errors, page, tests), known pattern.

### Large
**Signals:** "evaluate", "research", "migrate", "redesign", "investigate", 5+ files, unknowns exist
**Files created:** SPEC.md + mockups.md + plan.md + progress.md + findings.md
**Example:** "Migrate session storage to a shared cache" — research needed, many files, architectural decisions.

**Override:** User can always request a different size. Files can be added later (small can promote to medium).

## What to Do

### Starting a New Spec

1. **Validate name.** Convert to kebab-case, apply a useful component prefix when appropriate, and check `spec/{name}/` does not already exist.
2. **Create directory:** `mkdir -p spec/{name}/`
3. **Determine size** using heuristics above. Tell the user: "This looks like a **{size}** spec — I'll create {files}."
4. **Explore the codebase** for relevant context:
   - Read repo `AGENTS.md` and any relevant local `AGENTS.md` files
   - Read `CLAUDE.md` only if it exists and is not just a pointer to `AGENTS.md`
   - Read any relevant `.claude-docs/` files if the repo still uses them
   - Glob/Grep for related source files, existing patterns, similar features
5. **Write SPEC.md collaboratively.** Use [templates/spec.md](templates/spec.md) as the skeleton. Include the required `## ELI10` section near the top. Draft each section, discuss with the user, ask targeted questions. Do NOT auto-generate and dump.
   - **SAVE CHECKPOINT:** Write `spec/{name}/SPEC.md` as soon as the spec is agreed upon.
6. **Write mockups.md** using [templates/mockups.md](templates/mockups.md).
   - Always include a system/workflow view, even for backend-only work.
   - If the feature affects UI, include UI wireframes or interaction diagrams too.
   - **SAVE CHECKPOINT:** Write `spec/{name}/mockups.md` immediately after the first usable diagram set exists.
7. **Save progress.md** with status `speccing`, today's date, a session log entry, AND the recovery block at the top.
   - **SAVE CHECKPOINT:** Write `spec/{name}/progress.md` immediately.
8. **Save findings.md** (large specs only) with any research gathered in step 4.
   - **SAVE CHECKPOINT:** Write `spec/{name}/findings.md` immediately.
9. **Verify all files exist:** `ls -la spec/{name}/`

### Creating a Plan

1. **Read** `spec/{name}/SPEC.md` and `progress.md`.
2. **Explore the codebase** — Glob/Grep/Read to understand the implementation surface. Look for:
   - Existing patterns to follow (reference implementations)
   - Files that need modification
   - Test patterns for the category
3. **Write plan.md** using [templates/plan.md](templates/plan.md). Each step must reference specific files and have a verification method.
   - **SAVE CHECKPOINT:** Write `spec/{name}/plan.md` immediately after drafting.
4. **Refresh mockups.md** if codebase exploration changed the system shape, workflow sequence, or UI plan.
   - **SAVE CHECKPOINT:** Edit `spec/{name}/mockups.md` immediately when the diagrams need to change.
5. **Update progress.md** — Set status to `planned`, add session log entry.
   - **SAVE CHECKPOINT:** Edit `spec/{name}/progress.md` immediately.
6. **Verify files saved:** `ls -la spec/{name}/`

### Implementing

1. **Read all spec files** — SPEC.md, mockups.md, plan.md (if exists), progress.md.
2. **Present summary:** "Here's where we are: {status}. Last completed: {step}. Next: {action}."
3. **Work through steps.** If plan.md exists, follow its steps. Otherwise, work from SPEC.md acceptance criteria.
4. **Keep mockups.md current** when implementation changes architecture, workflow shape, operator flow, or UI behavior.
5. **Update progress.md after EVERY step** — Mark step complete, update Current Step and Next Action fields, add session log notes.
   - **SAVE CHECKPOINT:** Edit `spec/{name}/progress.md` after EACH completed step. This is the recovery mechanism.
6. **When done,** set progress.md status to `done`.

### Checking Status

**No args / general status:** Scan active `spec/*/progress.md` files. Do not include `spec-archive/*` unless the user asks for archived or historical specs. Show a table:

| Spec | Status | Current Step | Next Action |
|------|--------|--------------|-------------|

**Specific spec:** Show full progress.md contents for that spec.

## Progress Update Rules

These apply during planning and implementation:

- After completing each plan step → update progress.md (Current Step, Next Action, session log)
- When making a decision → add to Decisions table with rationale and date
- When hitting a blocker → add to Blockers list
- When encountering an error → add to Errors table with diagnosis
- When architecture, workflow, or UI shape changes → update `mockups.md`
- Before ending session → ensure latest session log entry has a **"Next:"** line

The "Next:" line is the most important field for cross-conversation recovery.

---

## Behavioral Rules

### Core Philosophy

**Context Window = RAM (volatile). Filesystem = Disk (persistent).**

Anything important gets written to disk. The conversation will be compacted or lost. The files survive.

### The 2-Action Rule

After every 2 search/browse/explore operations, save findings to `findings.md`. Don't accumulate research only in conversation — write it down before it gets compacted away.

### Read Before Decide

Re-read `plan.md` + `progress.md` before making major decisions. Don't rely on what you remember from earlier in the conversation — re-read the source of truth.

### 3-Strike Error Protocol

When something fails:

| Attempt | Action |
|---------|--------|
| 1 | Diagnose the error and fix it |
| 2 | Try an alternative approach (NEVER repeat the same failing action) |
| 3 | Broader rethink — step back and reconsider the approach |
| After 3 | Escalate to user. Log all attempts in progress.md Errors table. |

### 6-Question Reboot Test

If you're ever unsure where you are, answer these six questions. If you can't answer any of them, read the indicated file:

| Question | Source |
|---|---|
| Where am I? | Current Step in `progress.md` |
| Where am I going? | Remaining steps in `plan.md` |
| What's the goal? | Summary in `SPEC.md` |
| What does it look like? | `mockups.md` |
| What have I learned? | `findings.md` |
| What have I done? | Session Log in `progress.md` |

### Error Logging

Track errors in the Errors table in `progress.md`:

| Error | Diagnosis | Resolution | Date |
|-------|-----------|------------|------|

### Context Compaction Recovery

After `/clear` or context compression, follow this protocol:

1. Read `progress.md` — get status, current step, next action from header
2. Read the recovery block at the top of `progress.md` (it tells you exactly what to do)
3. Read `SPEC.md` for full requirements
4. Read `mockups.md` for the current system/workflow/UI shape
5. Read `plan.md` (if exists) for concrete steps
6. Read `findings.md` (if exists) for research context
7. Check recent changes: `git diff --stat` and `git log --oneline -5`
8. Run the 6-Question Reboot Test — verify you can answer all six
9. Present recovery summary and continue from Next Action

### Anti-Patterns

| Don't | Do Instead |
|---|---|
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log errors to progress.md Errors table |
| Start implementing without reading | Read spec files first |
| Repeat failed actions | Track attempts, mutate approach (3-Strike Rule) |
| Accumulate content in conversation | Write to disk immediately (2-Action Rule) |
| Leave diagrams implicit or in memory | Keep `mockups.md` current and concrete |
| Skip progress updates | Update after EVERY step |
| Continue from memory after compaction | Re-read all spec files (Recovery Protocol) |
| Auto-generate and dump a complete spec | Write collaboratively with the user |
