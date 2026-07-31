# Epics: Parent Spec + Numbered Child Specs

An **epic** is a goal too large to be one buildable spec. It is not a bigger `SPEC.md` — it is a thin
parent that owns the goal, plus numbered child specs that own the shippable slices.

```text
spec/local-intelligence-platform/     <- the epic
  EPIC.md                             destination, constraints, child index, fog, out of scope
  mockups.md                          whole-system diagram and cross-child workflows
  progress.md                         active child, epic-wide decisions, blockers
  findings.md                         shared research (optional)
  01-launch-surface/                  <- child spec, a normal /spec
    SPEC.md  mockups.md  progress.md  plan.md
  02-push-to-talk-dictation/
  03-meeting-recorder/
```

## The one rule that makes this work

**Detail lives in exactly one place.**

The parent is an *index*. It gists and links; it never restates a child's requirements, acceptance
criteria, or plan. The moment `EPIC.md` starts explaining *how* a child works, the epic has become
the mega-document it was meant to replace, and the two copies immediately start drifting.

| Belongs in `EPIC.md` | Belongs in the child |
|---|---|
| Destination and definition of done | Requirements and acceptance criteria |
| Constraints every child inherits | Technical approach, data model |
| Shared vocabulary | Implementation plan and steps |
| Ordered child index with one-line gists | Per-slice mockups and UI states |
| Not-yet-split work, out-of-scope rulings | Child-local decisions and blockers |

## When it is an epic

Reach for epic when either is true:

- You can already name three or more independently shippable slices.
- The alternative is one `SPEC.md` that nobody will read in a single sitting.

If the work is big but ships as one unit, that is **large**, not epic. Size is about *decomposition*,
not word count.

## Parent never gets a plan.md

Implementation belongs to children. A parent `plan.md` sequencing every file across every child is
the classic failure mode: it duplicates the children, goes stale on the first reorder, and cannot be
verified. If asked to implement an epic, redirect to the next child instead.

## Only one level

Children are `small`, `medium`, or `large` — never epics themselves. If a child truly needs to become
an epic, it has outgrown its parent: graduate it (see below) rather than nesting deeper.

## Numbering

- `NN-kebab-name`, starting at `01`, two digits.
- The number is **recommended delivery order**, not an identity or a dependency graph.
- If order changes, either renumber deliberately or leave a gap. Gaps are fine; churn is not.
- If child B genuinely cannot start until child A is done, say so in B's `progress.md` Blockers and
  in the parent's child-index gist. Never rely on the number to imply it.

## Splitting: what makes a good child

A child spec is a slice you could hand to a fresh agent session and get a shippable result from.

Good split axes:

- **User-visible capability** — the slice a user could actually notice.
- **Deployable boundary** — something that can merge and ship without its siblings.
- **Risk isolation** — a migration or spike that would otherwise contaminate steady work.

Bad split axes:

- By layer (`01-database`, `02-api`, `03-ui`) — nothing ships until all three land, so it is one
  spec wearing three hats.
- By file or module — that is a plan step, not a spec.
- By sprint or week — that is a schedule, not a scope.

## Fog: do not pre-create empty children

Create a child directory only when you can write its ELI10 and its mockups. Anything you can sense
but cannot yet shape stays in the parent's **Not Yet Split** section as prose.

The test is whether you can state the slice precisely now — *not* whether you can build it now. A
blocked-but-clear slice is a child. A vague-but-urgent one is not.

Empty numbered folders are fake clarity: they make the epic look decomposed while hiding the fact
that nobody has decided what goes in them.

## Context budget when working a child

A session working `03-meeting-recorder` reads:

1. The child's own files (`SPEC.md`, `mockups.md`, `plan.md`, `progress.md`).
2. The parent's ELI10, Shared Constraints, Shared Vocabulary, and child index.

It does **not** read sibling children. If a sibling's detail is genuinely required, that is a signal
the split was wrong or the shared fact belongs in the parent's constraints.

## Status is derived, not owned twice

Each child's `progress.md` is the source of truth for its status. The parent's child table is a
cached view — refresh it when a child changes phase, and treat any disagreement as the child being
right.

The epic's own status describes the *epic*, not the sum of its children:

| Status | Meaning |
|---|---|
| `speccing` | Destination and constraints still being written |
| `decomposing` | Destination settled; splitting work into children |
| `in-progress` | At least one child is being planned or built |
| `blocked` | Something stalls the epic across child boundaries |
| `done` | Every in-scope child is done and epic acceptance criteria pass |

## Graduating a child out

Occasionally a child grows into a long-lived product area of its own. Move it to top-level
`spec/{name}/` when it needs children of its own, or when it will outlive the epic.

When graduating:

1. Move the directory to `spec/{new-name}/` and drop the numeric prefix.
2. Clear the `Epic:` field in its `progress.md`, or repoint it if it now belongs elsewhere.
3. Copy — do not link — any inherited constraint it still depends on, since the parent may be
   archived later.
4. Replace its row in the parent's child index with a one-line pointer to the new location.

Graduation should be rare. Doing it often means the epic boundary was drawn wrong.

## Retrofitting an existing mega-spec

If a repository already has one giant spec that is really an epic:

1. Create `EPIC.md` from the existing summary, scope, and constraints.
2. Move implementable sections into `NN-` children, one per shippable slice.
3. Reduce the original document to gists and links — delete the moved prose rather than leaving both
   copies.
4. Push anything not yet sliceable into **Not Yet Split**.
5. Link pre-existing top-level specs that belong to the epic from the child index instead of moving
   them, if other work already references their paths.

## Archiving

Archive an epic as a whole tree: `spec-archive/{epic}/` keeps `EPIC.md` and every child together, so
the delivered slices stay readable next to the goal that produced them. Do not archive children
individually while the epic is active — mark them `done` instead.
