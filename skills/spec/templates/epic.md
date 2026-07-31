# Epic: {Epic Name}

## ELI10

Explain this epic in plain language:

- What are we building, overall?
- Why does it matter?
- Which child spec is the safest first slice?
- What are we explicitly not doing yet?

## Destination

What "this epic is finished" looks like. Write it concretely enough that anyone can tell whether a
proposed child spec moves toward it or past it. One or two paragraphs.

## Shared Constraints

Non-negotiables every child spec inherits. Keep these short and absolute — child specs must not
restate them, only comply with them.

-

## Shared Vocabulary

Terms that mean something specific inside this epic. Defining them once here stops child specs from
drifting into different names for the same thing.

| Term | Meaning |
|------|---------|

## Children

Delivery order. One line per child — a gist, not a summary. The child directory owns the detail.

Status is a cached view: the child's own `progress.md` is the source of truth. Refresh this table
whenever a child changes phase.

| # | Child spec | Status | Gist |
|---|------------|--------|------|
| 01 | [01-{child-name}](./01-{child-name}/) | speccing | One line: what this slice delivers |

## Not Yet Split

Work that belongs inside this epic but is not sharp enough to be a child spec yet. Write it as
loosely as the view allows. A patch here graduates into one or more child specs later — or turns out
to be unnecessary and is deleted.

Do not pre-create empty numbered directories for these. An empty child folder is fake clarity.

-

## Out of Scope

Work consciously ruled outside this epic's destination. This never graduates into a child spec; it
returns only as a separate epic.

-

## Acceptance Criteria

Epic-level only — coarse outcomes, not the union of every child's criteria.

- [ ] Every in-scope child spec is `done`
- [ ]

## Visual / System References

- See `mockups.md` for the whole-system diagram and cross-child workflows.

## Open Questions

-
