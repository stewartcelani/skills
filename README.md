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

# Install a specific skill (project-scoped)
npx skills add stewartcelani/skills --skill gpmc

# Global install (available in every project)
npx skills add -g stewartcelani/skills --skill gpmc

# Non-interactive / CI
npx skills add stewartcelani/skills --skill gpmc -g -y
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

## Repository layout

```
skills/
  gpmc/
    SKILL.md          # Agent instructions + YAML frontmatter
    scripts/          # Helper automation
```

Optional `skills.sh.json` controls grouping/order on the [skills.sh](https://skills.sh) repository page.

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

## License

MIT — see [LICENSE](./LICENSE).

## Author

[Stewart Celani](https://github.com/stewartcelani)
