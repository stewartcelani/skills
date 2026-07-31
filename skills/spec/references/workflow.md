# Spec Workflow Reference

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

### Epic
**Signals:** a product, platform, or goal with 3+ independently shippable slices; a single SPEC.md would be unreadable in one sitting
**Files created:** EPIC.md + mockups.md + progress.md (+ findings.md), plus `NN-{child}/` directories for the slices that are already sharp
**Example:** "Build the local intelligence platform" — dictation, meeting capture, and speaker attribution each ship separately.

Epic is about decomposition, not length. Big work that still ships as one unit is `large`.
Full guidance: [epics.md](epics.md).

**Override:** User can always request a different size. Files can be added later (small can promote to medium; large can promote to an epic).

## Naming

Spec names should be kebab-case under `spec/`. Prefix with the affected component or product area when that improves discoverability:

- `api-*`, `web-*`, `mobile-*`, `worker-*` — by surface
- `shared-*` / `platform-*` — genuinely cross-cutting work
- Follow any repository-local conventions documented in `AGENTS.md` (or equivalent)

Infer the prefix from the request and code surface when the user does not provide one.

Epic children are `NN-kebab-name` inside the epic directory, numbered from `01` in recommended
delivery order. The epic name already carries the context, so children do not repeat it:
`spec/local-intelligence-platform/02-push-to-talk-dictation/`, not `02-platform-push-to-talk`.

## Required Mockups

Every spec requires `mockups.md` — including an epic parent, where it holds the whole-system view and
any workflow that crosses child boundaries. It covers **both**:

- **System / process diagrams** (always) — architecture, workflows, data flow, sequence/state.
- **UI diagrams** (when user-facing) — screens, panels, states, interactions.

- Update `mockups.md` whenever architecture, workflow shape, or UI flow changes.
- This is the **golden first look** for “are we on the same page?” before code.

## Required ELI10

Every `SPEC.md` requires an `## ELI10` section immediately after the title and before `## Summary`.
Every `EPIC.md` requires one immediately after the title and before `## Destination`.

- Keep it short and plain.
- Explain what is changing, why it matters, the safest next step, and what is explicitly not
  happening yet.
- Update it whenever the scope, phase boundary, or next action changes.

## Rush review order

1. `SPEC.md` → `## ELI10` bullets
2. `mockups.md` (UI **and** system/process diagrams)

Only then deeper docs (`plan.md`, findings, full requirements).

## Progress Update Rules

Update `progress.md`:
- **After completing each plan step** — Mark step complete, update Current Step and Next Action header fields
- **When making a decision** — Add row to Decisions table with rationale
- **When hitting a blocker** — Add to Blockers list
- **When encountering an error** — Add to Errors table with diagnosis and resolution
- **When architecture, workflow, or UI shape changes** — Update `mockups.md`
- **Before ending a session** — Ensure the latest session log entry has a "Next:" line

The "Next:" line is the single most important field. It's what makes cross-conversation recovery work: the next agent reads it and knows exactly what to do.

## Context Compaction Recovery

When resuming after context compaction or `/clear`, read files in this order:

1. `progress.md` — Machine-readable header gives instant context (status, current step, next action). The recovery block at the top has step-by-step instructions.
2. `SPEC.md` — Full requirements for reference
3. `mockups.md` — Current system/workflow/UI diagrams
4. `plan.md` (if exists) — Concrete steps and current position
5. `findings.md` (if exists) — Research context

Inside an epic, start at the parent's `progress.md` to find the Active Child, read the parent's
`EPIC.md` for destination and shared constraints, then recover the active child normally. Do not load
sibling children.

Then run:
- `git diff --stat` — What changed since last session
- `git log --oneline -5` — Recent commits for context

Run the 6-Question Reboot Test:

| Question | Source |
|---|---|
| Where am I? | Current Step in `progress.md` |
| Where am I going? | Remaining steps in `plan.md` |
| What's the goal? | Summary in `SPEC.md` |
| What does it look like? | `mockups.md` |
| What have I learned? | `findings.md` |
| What have I done? | Session Log in `progress.md` |

Present a recovery summary:
> Last session: {date}. Status: {status}. Last completed: {step}. Next: {action}.

## Collaborative Spec Writing

When writing a spec, do NOT auto-generate a complete document and dump it. Instead:

1. Read relevant codebase context (CLAUDE.md, .claude-docs/, source files)
2. Draft each section and discuss with the user
3. Ask targeted questions to fill gaps
4. Iterate on requirements and acceptance criteria together
5. Only finalize when the user confirms

The goal is a spec that captures the user's intent accurately, not a template filled with generic content.

For an epic, interview **breadth-first** before writing: destination, inherited constraints, first
shippable slice, explicit exclusions. `/grill-me` is the natural tool for this. Depth comes later,
inside each child.

## Relationship to Existing Systems

### docs/PRDs/ (Legacy)
The `docs/PRDs/` directory contains legacy product requirement documents. New features should use `spec/` instead. No migration needed — legacy PRDs stay as-is.
