# stewartcelani/skills

Agent skills for AI coding tools, installable with the [Vercel Labs `skills` CLI](https://skills.sh) (`npx skills`). Each skill gives an agent a focused workflow, local tooling, or domain knowledge it would not otherwise have.

[![skills.sh](https://skills.sh/b/stewartcelani/skills)](https://skills.sh/stewartcelani/skills)

## Install

```bash
# Interactive picker or catalogue
npx skills add stewartcelani/skills
npx skills add stewartcelani/skills --list

# One project-scoped skill
npx skills add stewartcelani/skills --skill spec

# All skills in this repository
npx skills add stewartcelani/skills --skill spec --skill codex-session --skill claude-session --skill ship --skill gpmc

# Global install
npx skills add -g stewartcelani/skills --skill spec
```

Works with Claude Code, Cursor, Codex, OpenCode, Windsurf, GitHub Copilot, Cline, and other tools supported by the CLI.

## Choose a skill

| Area | Skill | Use it when you need to… |
|---|---|---|
| Development | [`spec`](./skills/spec/) | Plan and persist non-trivial engineering work — from a one-file fix to a multi-slice epic — in durable feature files. |
| Development | [`codex-session`](./skills/codex-session/) | Recover a local Codex task by GUID, title, phrase, or recent activity. |
| Development | [`claude-session`](./skills/claude-session/) | Recover a local Claude Code conversation by GUID, title, phrase, or recent activity. |
| Development | [`ship`](./skills/ship/) | Intentionally commit and push every current Git-trackable change in one operation. |
| Sysadmin | [`gpmc`](./skills/gpmc/) | Inventory Active Directory Group Policy safely, without RSAT. |

## Development

### `spec` — durable, spec-driven engineering

Use `/spec` for non-trivial work: a feature, migration, redesign, investigation, or any task that must survive a long session or be handed to another agent.

```text
User request
    ↓
spec/<feature>/ on disk
    ├── SPEC.md       Goal, scope, acceptance criteria, ELI10
    ├── mockups.md    System/process diagrams and UI shape
    ├── progress.md   Current step, next action, recovery state
    ├── plan.md       File-specific implementation plan
    └── findings.md   Research for larger work
```

Start it with:

```text
/spec
write a spec for webhook retries
plan the implementation for X
where are we on X?
```

Why it exists:

- Context windows are temporary; the `spec/` tree is durable.
- `progress.md` captures the exact next action so another session can resume without re-deriving context.
- `SPEC.md` starts with a plain-English ELI10 explanation.
- `mockups.md` is the fast alignment check: system/process diagrams always, plus UI diagrams when relevant.

For a fast review, read `SPEC.md` → `## ELI10` first, then `mockups.md`. If either is wrong, fix the shape before planning or implementation.

#### Epics — when the goal is bigger than one spec

Work is sized `small`, `medium`, `large`, or `epic`. An epic is a goal with three or more independently shippable slices. Rather than one enormous `SPEC.md`, it becomes a thin parent that owns the goal plus numbered child specs that own the slices:

```text
spec/<epic>/
    ├── EPIC.md       Destination, inherited constraints, child index, not-yet-split, out of scope
    ├── mockups.md    Whole-system view and cross-child workflows
    ├── progress.md   Active child, epic-wide decisions and blockers
    ├── 01-<child>/   A normal spec, sized on its own merits
    └── 02-<child>/
```

The parent is an index, so detail lives in exactly one place: it gists and links, never restates. It gets no `plan.md` — planning and building happen inside children. A session working child `02` loads that child plus the parent's constraints, not its siblings, which is what keeps a long-running epic inside one context window.

Slices you cannot specify yet stay as prose under **Not Yet Split** instead of becoming empty folders, since an empty numbered directory looks decomposed without anyone having decided what goes in it. Numbers are recommended delivery order, not identity — real dependencies are recorded in the child's blockers.

```text
spec out the local intelligence platform     # creates the epic
add a child spec for meeting recording       # creates 03-meeting-recording/
where are we on the platform?                # epic status with children indented
```

Pair it with a breadth-first interview (`/grill-me`) when charting the epic: settle the destination, the constraints every child inherits, the first shippable slice, and what is explicitly excluded. Depth comes later, inside each child. See [`skills/spec/references/epics.md`](./skills/spec/references/epics.md) for splitting heuristics, retrofitting an existing mega-spec, graduation, and archiving.

### `codex-session` — recover local Codex tasks

Use this when a Codex task died, exhausted context, ran out of quota, crashed, or you simply want to see what you have been working on locally.

```text
/codex-session
    ↓
recent local tasks
    ↓
choose by GUID, title, phrase, or latest
    ↓
inspect task history and current project state
    ↓
resume here, start fresh, or hand off to Claude
```

Examples:

```text
/codex-session
/codex-session latest
/codex-session <GUID>
/codex-session "Blah Blah"
/codex-session "distinctive remembered phrase"
```

It reads local Codex task metadata and persisted transcripts, then verifies the current repository before declaring the work complete or ready to continue. A Claude handoff is optional—not the main purpose.

### `claude-session` — recover local Claude Code conversations

Use this for the same recovery flow with local Claude Code conversations. It works on Windows, macOS, and Linux and can inspect Desktop-driven sessions when they are persisted in Claude Code’s local store.

```text
/claude-session
/claude-session latest
/claude-session <GUID>
/claude-session "Blah Blah"
/claude-session "distinctive remembered phrase"
```

It finds conversations by recency, session ID, title, or a phrase in the transcript; then it reports the working directory, branch, recent messages, tools, referenced artifacts, and current state. It does not yet read ordinary standalone Claude Desktop chat storage.

When moving recovered work to a new Claude conversation or Codex, either session skill can create a compact, redacted recovery packet containing the goal, constraints, completed work, decisions, verification, blockers, and next action. The recipient should still inspect the repository and referenced artifacts.

### `ship` — commit and push everything

Use `/ship` when you deliberately want one commit containing every current Git-trackable working-tree change, followed by a push of the current branch. It is the opposite of a selective, tidy-commit workflow.

```text
/ship
  ↓
git add -A
  ↓
one accurate commit
  ↓
push current branch
```

Mixed, broad, generated, staged, unstaged, untracked, or unrelated-looking changes are included without prompting. Git-ignored files remain ignored unless you explicitly name them. It does not open a pull request, rebase, force-push, or bypass failed hooks unless you explicitly ask.

## Sysadmin

### `gpmc` — read-only Active Directory Group Policy inventory

Use this on a domain-joined Windows host to list GPOs, inspect domain/OU/site links, find unlinked policies, search by name, or see the current user's RSoP. It does not require the RSAT Group Policy module.

```text
Domain LDAP + current user
          ↓
read-only GPO and gPLink inventory
          ↓
linked / unlinked / enabled / disabled / enforced results
```

Normal authenticated domain users can usually read GPO containers and `gPLink` attributes by design. This is read-only domain inventory—not full RSoP for arbitrary users or computers, because security filtering and WMI filters still matter.

On a domain-joined Windows host:

```powershell
# Replace <skill-dir> with the installed gpmc skill directory.
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action summary
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action unlinked
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action gpo -Name "VPN"
```

Actions: `list` · `unlinked` · `links` · `links-on` · `gpo` · `search` · `rsop-user` · `summary` · optional `-Json`.

## Repository layout

```text
skills/
  spec/
    SKILL.md
    references/     workflow.md, epics.md
    templates/      spec.md, epic.md, mockups.md, plan.md, progress.md, epic-progress.md, findings.md
  codex-session/
    SKILL.md
    scripts/
  claude-session/
    SKILL.md
    scripts/
  ship/
    SKILL.md
  gpmc/
    SKILL.md
    scripts/
```

[`skills.sh.json`](./skills.sh.json) controls the grouping and order on the skills.sh repository page.

## Day-to-day CLI

```bash
npx skills list
npx skills find <query>
npx skills check
npx skills update
npx skills remove <skill>
```

## Security

- Treat skills like code and review `SKILL.md` plus any scripts before use in sensitive environments.
- `gpmc` is intentionally read-only.
- `spec` writes under `spec/`; implementation outside that tree follows user approval.
- `codex-session` and `claude-session` read local conversation records without modifying them and redact sensitive excerpts by default.
- `ship` deliberately stages and pushes every Git-trackable worktree change when explicitly invoked.

## License

MIT — see [LICENSE](./LICENSE).

## Author

[Stewart Celani](https://github.com/stewartcelani)
