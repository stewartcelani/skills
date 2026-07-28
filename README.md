# stewartcelani/skills

Agent skills for AI coding tools — installable with the [Vercel Labs `skills` CLI](https://skills.sh) (`npx skills`).

[![skills.sh](https://skills.sh/b/stewartcelani/skills)](https://skills.sh/stewartcelani/skills)

These skills give agents specialized, procedural knowledge (workflows, checklists, scripts) that generic models don’t have baked in.

## Install

```bash
# Interactive — pick skills from this repo
npx skills add stewartcelani/skills

# List what’s available first
npx skills add stewartcelani/skills --list

# Install specific skills (project-scoped)
npx skills add stewartcelani/skills --skill gpmc
npx skills add stewartcelani/skills --skill spec

# Install both
npx skills add stewartcelani/skills --skill gpmc --skill spec

# Global install (available in every project)
npx skills add -g stewartcelani/skills --skill spec

# Non-interactive / CI
npx skills add stewartcelani/skills --skill spec -g -y
```

Works with Claude Code, Cursor, Codex, OpenCode, Windsurf, GitHub Copilot, Cline, and many other agents supported by the CLI.

## Skills

### Sysadmin

Windows / Active Directory operational tooling for domain environments.

| Skill | Description |
|-------|-------------|
| [`gpmc`](./skills/gpmc/) | Read-only Active Directory Group Policy inventory via LDAP — list GPOs, link topology (enabled/disabled/enforced), unlinked GPOs, search, and current-user RSoP. No RSAT required. Domain-agnostic (RootDSE). Windows + domain-joined. |

#### gpmc (quick start)

On a domain-joined Windows host:

```powershell
# After install, skill-dir is typically .agents/skills/gpmc or .claude/skills/gpmc
powershell.exe -ExecutionPolicy Bypass -File ".\.agents\skills\gpmc\scripts\Query-Gpo.ps1" -Action summary
powershell.exe -ExecutionPolicy Bypass -File ".\.agents\skills\gpmc\scripts\Query-Gpo.ps1" -Action unlinked
powershell.exe -ExecutionPolicy Bypass -File ".\.agents\skills\gpmc\scripts\Query-Gpo.ps1" -Action gpo -Name "VPN"
```

Actions: `list` · `unlinked` · `links` · `links-on` · `gpo` · `search` · `rsop-user` · `summary` · optional `-Json`.

### Development

Spec-driven engineering process for any codebase.

| Skill | Description |
|-------|-------------|
| [`spec`](./skills/spec/) | Spec-driven development under `spec/{feature}/`. Collaborative specs, mockups, plans, progress recovery, optional SQL runbooks and GOAL handoff. Spec turns stay write-scoped to `spec/` until you approve implementation. |

#### spec (quick start)

```bash
npx skills add stewartcelani/skills --skill spec
```

Then in any project, ask the agent things like:

- `/spec` or “write a spec for webhook retries”
- “plan the implementation for X”
- “where are we on X” / “spec status”
- “write GOAL.md” (handoff only after you’ve accepted the spec)

Typical layout created for a feature:

```
spec/my-feature/
  SPEC.md          # Requirements + ELI10
  mockups.md       # System / workflow / UI diagrams
  progress.md      # Status, session log, recovery block
  plan.md          # Implementation steps (medium+)
  findings.md      # Research notes (large)
  sql-runbook.md   # Draft SQL if schema changes
  GOAL.md          # Optional execution contract
```

## Repository layout

```
skills/
  gpmc/
    SKILL.md
    scripts/
  spec/
    SKILL.md
    references/
    templates/
```

Optional `skills.sh.json` controls grouping/order on the [skills.sh](https://skills.sh) repository page (**Sysadmin**, **Development**).

## Day-to-day CLI

```bash
npx skills list          # what’s installed
npx skills find [query]  # search the ecosystem
npx skills check         # see what’s outdated
npx skills update        # update installed skills
npx skills remove        # uninstall
```

## Security

- Treat skills like code. Scripts may run commands on your machine.
- Review `SKILL.md` and any `scripts/` before installing in sensitive environments.
- `gpmc` is intentionally **read-only** (LDAP query + local `gpresult`).
- `spec` writes under `spec/` by design; implementation outside that tree only after you approve.

## License

MIT — see [LICENSE](./LICENSE).

## Author

[Stewart Celani](https://github.com/stewartcelani)
