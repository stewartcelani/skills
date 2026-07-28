# Spec Workflow Reference

Companion notes for the `spec` skill. Prefer `SKILL.md` as the source of truth;
use this file for quick refresh after context compaction.

## Adaptive sizing

| Size | Signals | Files |
|------|---------|-------|
| Small | fix / tweak / rename / single file | SPEC + mockups + progress |
| Medium | add / build / 2–5 files / sequenced steps | + plan |
| Large | research / migrate / redesign / unknowns | + findings |

Tell the user the size you picked and why. Promote later if needed.

## Naming

- Kebab-case feature folder under `spec/`
- Optional area prefix for discoverability (`api-…`, `web-…`, `mobile-…`, `shared-…`)
- Infer from request + code surface when the user does not name it
- Follow repository-local conventions when documented in `AGENTS.md` / similar

## Required artifacts

- **`mockups.md`** — system/workflow always; UI when relevant; keep current
- **`## ELI10` in SPEC.md** — plain language; update with scope changes
- **Recovery block** in `progress.md` — copy verbatim from the template
- **`sql-runbook.md`** — when schema/SQL changes are in scope

## Progress updates

- After each plan step → Current Step, Next Action, session log
- Decisions / blockers / errors → tables in `progress.md`
- Architecture or UI shape change → update `mockups.md`
- End of session → latest log entry has **`Next:`**

## Compaction recovery order

1. `progress.md`
2. `SPEC.md`
3. `mockups.md`
4. `plan.md` (if present)
5. `findings.md` / `GOAL.md` (if present)
6. `git diff --stat` && `git log --oneline -5`
7. 6-Question reboot test
8. Summarize and continue from Next Action

## Collaborative writing

1. Read relevant codebase context
2. Draft sections; discuss with the user
3. Ask targeted questions for gaps
4. Iterate requirements and acceptance criteria
5. Finalize only when the user confirms

Do not auto-generate and dump a full document as a first move.

## Spec vs implementation

| Phase | Writes under `spec/` | Application code |
|-------|----------------------|------------------|
| `/spec` / plan / findings | Yes | No |
| Explicit implement / build / apply | Yes (progress) | Yes |
