---
name: codex-session
description: Find and inspect local Codex task conversations, including by session GUID, title, recent activity, or a phrase from the conversation. Use when the user runs `/codex-session`, says a prior Codex conversation died or ran out of context, wants to resume a named task, asks what a local Codex task did, or wants to continue that work in Codex or Claude.
---

# Codex Session

Find persisted local Codex task conversations on the current machine, understand what they were doing, and help the user resume or hand off the work. The primary job is **conversation discovery and recovery**; a transfer to another agent is optional.

## What to Use

```text
/codex-session <GUID>       Inspect one known Codex task.
/codex-session latest       Find the most recent local task.
/codex-session "Task name" Find a task by its title.
/codex-session              What have I been working on lately? Show recent local tasks and ask which to inspect.
```

Use this when a task died because of context exhaustion, a crash, quota exhaustion, or an interrupted session. Local transcripts and task metadata can still reveal the user intent, work completed, decisions, errors, referenced files, and last next step.

## Local Discovery Workflow

```text
[GUID, task title, phrase, or "latest"]
                 |
                 v
[Local Codex task index + transcripts]
                 |
                 v
[Inspect selected task and referenced artifacts]
                 |
                 v
[Resume here | start a new task | hand off to Claude]
```

Use `<python>` for an available Python 3 launcher and `<skill-dir>` for this skill's directory.

```text
# Recent tasks for the current project; omit --cwd to search every project.
<python> "<skill-dir>/scripts/monitor_active_sessions.py" --cwd "<project-root>" --recent 8 --details

# Find a task by its visible title or a distinctive remembered phrase.
<python> "<skill-dir>/scripts/monitor_active_sessions.py" --title "Blah Blah" --recent 8 --details
<python> "<skill-dir>/scripts/monitor_active_sessions.py" --query "distinctive phrase" --recent 8 --details

# Inspect a known session GUID.
<python> "<skill-dir>/scripts/inspect_session.py" <session-guid>
```

Use `--query` for an exact phrase from a conversation. Search transcripts only; do not read or dump shell snapshots by default.

## Inspect and Recover

1. Use the GUID directly when supplied. Otherwise list recent tasks, filter by title, or search an exact distinctive phrase.
2. Read the task summary: title, user requests, goals, final/last assistant message, recent commands, referenced files, and task completion state.
3. Read current durable sources directly: repository status, recent history, specifications, plans, progress/readiness documents, changed files, and relevant test or build evidence.
4. If the old task and current files disagree, explain the difference and trust current durable project state.
5. Report the current status: **complete**, **ready to resume**, **paused**, **blocked**, **superseded**, or **uncertain**.
6. Give the immediate next action. Start a new task only if the old conversation cannot be resumed in place or the user asks for a fresh task.

## Continuing in Another Agent

When the user wants to continue in a new Codex task or Claude thread, produce a concise, redacted recovery packet after inspection:

```markdown
## Recovered task
- Codex session: <GUID>
- Title: <task title>
- Repository: <path and branch when known>

## Goal and constraints
- <material user requirements>

## Work completed and decisions
- <completed work and rationale>

## Current verified state
- <durable files, tests, repository state, contradictions>

## Blockers and next action
- <one concrete safe next step>
```

The packet is a handoff aid, not a replacement for discovery. Include the session GUID and durable artifact paths so the next agent can inspect the local conversation and current files itself.

## Safety

- Do not dump raw transcript chunks, tool output, shell snapshots, or environment values by default.
- Redact passwords, tokens, API keys, cookies, authorization headers, and private environment values from excerpts.
- Treat task history as evidence, not proof that work is complete now.
- Do not modify session records or project files while inspecting unless the user explicitly asks.
