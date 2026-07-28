---
name: gpmc
description: >
  Read-only Active Directory Group Policy inventory via LDAP — list GPOs, show
  OU/site links (enabled/disabled/enforced), find unlinked GPOs, search by name,
  and gpresult for the current user. Use when the user asks about GPOs, Group
  Policy, GPMC, linked vs unlinked policies, RSoP, what applies to this user, or
  runs /gpmc. Does not require RSAT GroupPolicy module. Domain-agnostic (uses
  RootDSE). Never writes or edits GPO links.
license: MIT
compatibility: Requires a domain-joined Windows host (or network path to a DC)
  with LDAP access as the current user, and PowerShell 5.1+.
argument-hint: "[list|unlinked|links|gpo|rsop|search|summary] [name]"
metadata:
  audience: system administrators
  tools: powershell,ldap,gpresult
  access: read-only
  os: windows
---

# Group Policy inventory (read-only LDAP)

Use this skill when the user asks about domain Group Policy Objects, what is
linked where, unlinked/orphaned GPOs, GPO enabled/disabled flags, or what
applies to the **current** interactive user on this PC.

## What this skill does

- Inventory all GPOs under `CN=Policies,CN=System,<domainDN>`
- Parse `gPLink` on domain / OU / site objects (link order, disabled, enforced)
- Find GPOs that exist but are **not linked** anywhere
- Search GPOs by display name
- Show `gpresult` for the **current user** on this workstation
- Prefer the helper script so link/flag parsing stays consistent

Domain DN is discovered automatically via `LDAP://RootDSE` — no hardcoded domain.

## What this skill does **not** do

- Edit, create, delete, or link GPOs
- Open the GPMC GUI or require the RSAT `GroupPolicy` module
- Claim full computer RSoP without elevation (`gpresult /scope computer` is
  Access Denied for a non-elevated user)
- Answer “exactly what applies to another user/PC” as true RSoP (security
  filtering + WMI need modeling rights). Best-effort: show GPOs linked on their
  OU path

## Important mental model

| Source | Answers |
|---|---|
| Local client cache / applied history | Only what applied to **this** machine/user |
| Domain LDAP (`groupPolicyContainer` + `gPLink`) | Domain-wide inventory + **linked vs unlinked** |
| `gpresult /scope user` | Applied user GPOs for **this** session user |

Clients do **not** sync the full link topology. Domain LDAP from a normal domain
user typically **does** (GPC objects and OU `gPLink` are readable without admin
rights in most environments).

## How to work

1. Run the helper script for structured answers (default).
2. For “what hit me on this PC?”, also run `gpresult /r /scope user`.
3. Present tables: name, GUID, flags, link targets, enabled/disabled/enforced.
4. Never propose write actions unless the user explicitly asks for change
   guidance — and even then, do **not** execute writes from this skill.

## Helper script

All commands below use `<skill-dir>` — the base directory of this skill (the
folder containing this `SKILL.md`). Substitute it verbatim; do not assume any
particular user profile path.

```powershell
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action <action> [options]
```

| Action | Purpose | Example |
|---|---|---|
| `list` | All GPOs | `-Action list` |
| `unlinked` | GPOs with no domain/OU/site link | `-Action unlinked` |
| `links` | All containers that have `gPLink`, expanded | `-Action links` |
| `links-on` | Links on one OU/domain DN or name fragment | `-Action links-on -Name "Sales"` |
| `gpo` | One GPO + everywhere it is linked | `-Action gpo -Name "Map Network Drives"` |
| `search` | Name contains | `-Action search -Name "VPN"` |
| `rsop-user` | `gpresult /r /scope user` (this user) | `-Action rsop-user` |
| `summary` | Counts: total / linked / unlinked | `-Action summary` |

Optional: `-Json` for machine-readable output.

### Locating `<skill-dir>`

Common install locations after `npx skills add`:

- `.agents/skills/gpmc/`
- `.claude/skills/gpmc/`
- `~/.agents/skills/gpmc/` (global)

If the agent already has the skill path from load metadata, use that.

## Flag / link encoding (quick reference)

**GPO `flags` (on the GPC object):**

| Value | Meaning |
|---|---|
| 0 | User + Computer configs enabled |
| 1 | User config disabled |
| 2 | Computer config disabled |
| 3 | Both disabled |

**`gPLink` options (per link `;N]`):**

| N | Meaning |
|---|---|
| 0 | Link enabled |
| 1 | Link disabled |
| 2 | Link enforced (enabled) |
| 3 | Link disabled + enforced |

Link order in the `gPLink` string is **LSF first** as stored. GPMC displays with
higher precedence first — the script labels **Precedence** (GPMC-style, 1 =
highest) clearly.

## Configuration

- Domain: auto via `RootDSE.defaultNamingContext`
- Configuration NC (sites): auto via `RootDSE.configurationNamingContext`
- Auth: current Windows user (Integrated) — no special credentials
- RSAT: **not required**

## Common workflows

### “Is GPO X linked?”

```powershell
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action gpo -Name "Map Network Drives"
```

### “What GPOs are unlinked?”

```powershell
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action unlinked
```

### “What is linked under this OU?”

```powershell
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action links-on -Name "OU=Users,OU=Sales,DC=example,DC=com"
```

### “What user policies apply to me here?”

```powershell
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action rsop-user
```

### Quick health snapshot

```powershell
powershell.exe -ExecutionPolicy Bypass -File "<skill-dir>\scripts\Query-Gpo.ps1" -Action summary
```

## Pairing with directory tools

- Use your AD / identity skill (or `Get-ADUser` / LDAP) for users, groups,
  computers, and OU structure.
- Use this skill for GPO objects, link topology, unlinked inventory, and local
  user RSoP.
- To reason about “policies for Alice”: resolve Alice’s DN/OU, then run
  `links-on` along that OU path (inheritance) — note security filtering may
  still exclude her.

## Limitations

- Computer RSoP on this workstation needs elevation; do not pretend computer
  GPOs from `gpresult` unless it succeeds.
- WMI filters and security filtering are not fully evaluated by LDAP link
  inventory alone.
- SYSVOL setting details (`Registry.pol`, scripts) are optional deep-dives —
  only open when the user asks what a GPO *contains*.
- Read-only: no `Set-GPLink`, no GPMC edits.
- Requires network reachability to a domain controller (VPN if remote).

## Error handling

| Symptom | Fix |
|---|---|
| LDAP bind / Policies container failure | Confirm domain connectivity / VPN; retry on a domain-joined host |
| Empty `gPLink` on OU | OU has no direct links (may still inherit) |
| `gpresult` Access Denied | Use `-Action rsop-user` only; computer scope needs admin |
| Name matches many GPOs | Show candidates; ask which GUID/name |
| Running on non-Windows / non-domain host | This skill cannot query domain GPO topology from that environment |

## Security notes

- The script is **read-only** LDAP + local `gpresult`. Review it before running
  in locked-down environments.
- Output may include GPO names and OU structure — treat as internal directory
  metadata; do not paste full dumps into public tickets without need.
- Never store or hardcode credentials in this skill.
