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

#### gpmc — works as a normal domain user

You do **not** need Domain Admin, a “GPO admin” role, or the RSAT Group Policy module.

That’s how Active Directory is designed: authenticated domain users can normally **read** Group Policy Containers (`groupPolicyContainer`) and `gPLink` attributes on domain/OU/site objects over LDAP. Clients never get a full link topology locally — they only see what applied to them — but a domain-joined workstation (or any host that can reach a DC) can query the directory as the signed-in user.

So this skill is:

- **Read-only inventory** for the whole domain’s GPO *objects* and *links* (enabled / disabled / enforced)
- Runnable by **any normal domain user** with default read rights (unusual locked-down forests may differ)
- Free of GPMC GUI / RSAT dependency (pure LDAP + optional local `gpresult`)
- **Not** full RSoP for *other* users/PCs (security filtering + WMI still matter); not computer RSoP without elevation

#### gpmc (quick start)

On a domain-joined Windows host, as your normal domain account:

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
| [`spec`](./skills/spec/) | Spec-driven development under `spec/{feature}/`. Collaborative specs with required ELI10 + mockups, adaptive sizing, plan/progress recovery, and compaction reboot protocol. Intent from natural language — no subcommands. |

#### Why `/spec` (how I actually use it)

I run this for **any non-trivial work** — which in practice is almost everything past a one-liner fix. Specs live as real markdown under `spec/{feature}/`, not as chat vapor.

What that buys you:

- **Multi-day goals stay on rails.** Context windows compact and sessions die; the files don’t. `progress.md` always has a recovery block and a **Next:** line so the next session (or a cold agent) can resume without re-deriving the plan from memory.
- **Handoffs are cheap.** Point another model (or another person) at the same `SPEC.md` + `mockups.md` + `plan.md` + `progress.md`. They can implement, critique, or continue without the original conversation.
- **Spec review is first-class.** Before code, you get something reviewable. Easy to send to a second model for a “does this make sense?” pass.
- **No planning mode tax.** With a solid `spec/` tree I stopped relying on each product’s ephemeral “plan mode.” The plan is durable files, portable across Claude / Codex / Cursor / whatever. One workflow, any model.

##### Rush review order (you or another model)

When you’re short on time, don’t read the whole tree first:

1. **`SPEC.md` → `## ELI10`** — the bullet points at the top. Plain language: what’s changing, why, safest next step, what’s *not* happening yet.
2. **`mockups.md`** — the **golden first look**. Diagrams / workflows / wireframes that prove you and the model are on the same page about *shape* before anyone writes code.

If those two disagree with what you wanted, fix them and stop. Everything else (`plan.md`, acceptance criteria, findings) is downstream of that alignment.

`mockups.md` is not optional filler. Even for backend-only work it should show the workflow, data flow, or before/after shape. That file is the fastest way to catch “the model built a different product than I meant.”

##### Reading specs anywhere (Obsidian)

I **symlink the project’s `spec/` tree into an Obsidian vault** (the vault is *not* the git repo — just a viewer/sync surface). Obsidian Sync (or your preferred sync) then hits every device:

- Code and agents on a remote box over **SSH**
- Read / annotate the same markdown on **desktop, Mac, or phone** in Obsidian

Agents still write through the project path (`spec/...`). The symlink means those files show up as normal notes in the vault without duplicating content or committing the vault into the codebase.

The skill keeps agents honest during a pure `/spec` turn: research and write under `spec/` only, then stop for approval before implementation.

#### spec (quick start)

```bash
npx skills add stewartcelani/skills --skill spec
```

Then in any project, ask the agent things like:

- `/spec` or “write a spec for webhook retries”
- “plan the implementation for X”
- “let’s build X” / “implement X”
- “where are we on X” / “spec status”

Typical layout created for a feature:

```
spec/my-feature/
  SPEC.md          # Requirements + required ELI10
  mockups.md       # System / workflow / UI diagrams (required)
  progress.md      # Status, session log, recovery block
  plan.md          # Implementation steps (medium+)
  findings.md      # Research notes (large)
```

Templates live in the skill under `templates/`; workflow notes under `references/workflow.md`.

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
