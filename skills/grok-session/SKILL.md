---
name: grok-session
description: Find and inspect local Grok CLI conversations by session GUID, title, phrase, or recent activity. Use when the user runs `/grok-session`, asks what Grok work they have been doing lately, says a Grok conversation died, ran out of context, crashed, or exhausted usage, wants to resume a named session, or wants to continue it in Grok, Claude, or Codex.
---

# Grok Session

Find persisted local Grok CLI conversations on the current machine, inspect what happened, and recover the work. A handoff to a new Grok session, Claude, or Codex is an optional use after the conversation is found and understood.

## What to Use

```text
/grok-session              What have I been working on lately? List recent local sessions.
/grok-session <GUID>       Inspect one known Grok session.
/grok-session latest       Inspect the most recent local session.
/grok-session "Blah Blah" Find a session by title or a remembered phrase.
```

Use this when a prior Grok conversation died from context exhaustion, a crash, login or usage trouble, compaction loss, or an interrupted session. Its local transcript can still reveal the user intent, work completed, decisions, errors, referenced files, and last next step.

## Scope

- Read Grok CLI records stored under the current user's `.grok` directory (or `GROK_HOME`): per-workspace session dirs, `summary.json`, `updates.jsonl`, `chat_history.jsonl` (fallback), `signals.json`, `plan.json`, `active_sessions.json`, and the local `session_search.sqlite` index.
- Work on Windows, macOS, and Linux. Resolve the default store from the home directory, or pass `--grok-home` for a copied or mounted store.
- Do not claim to read grok.com web chat history; that is a separate product store and is not supported.
- Do not read `auth.json`, rewind file snapshots, or `terminal/` command logs by default — those often contain secrets or bulky raw output.

## Local Discovery Workflow

```text
[recent | GUID | title | phrase]
                  |
                  v
[Local Grok session store (~/.grok)]
                  |
                  v
[Inspect selected transcript + current project state]
                  |
                  v
[Resume in Grok | start a new Grok session | continue in Claude/Codex]
```

Use `<python>` for an available Python 3 launcher and `<skill-dir>` for this skill's directory.

```text
# Recent sessions for every project or just this project.
<python> "<skill-dir>/scripts/grok_sessions.py" monitor --recent 8 --details
<python> "<skill-dir>/scripts/grok_sessions.py" monitor --cwd "<project-root>" --recent 8 --details

# Find by visible title or a distinctive remembered phrase.
<python> "<skill-dir>/scripts/grok_sessions.py" monitor --title "Blah Blah" --recent 8 --details
<python> "<skill-dir>/scripts/grok_sessions.py" monitor --query "distinctive phrase" --recent 8 --details

# Inspect a known session GUID.
<python> "<skill-dir>/scripts/grok_sessions.py" inspect <session-guid>
```

For a copied, mounted, or remote-accessible Grok store, add `--grok-home "<path-to-.grok>"` before the command. `GROK_HOME` is honored when `--grok-home` is omitted.

Optional Grok CLI helpers (when installed) for listing/search confirmation only — prefer the Python scripts for redacted, structured recovery. Do not paste `grok export` output into chat; it is unredacted.

```text
grok sessions list --limit 20
grok sessions search "keyword"
```

## Inspect and Recover

1. With no identifier, list recent sessions and present the likely matches. Ask which one to inspect if the user has not identified it.
2. Use the GUID directly when supplied. Otherwise filter by title or search a distinctive remembered phrase.
3. Read the session summary: title, user requests, latest assistant message, recent tools, working directory, branch, model, token/context usage, plan/todos, referenced artifacts, and live PID if active.
4. Read the current project state directly: repository status, recent history, specifications, plans, progress/readiness documents, changed files, and relevant test or build evidence.
5. If the old session and current files disagree, explain the difference and trust current durable project state.
6. Report the current status: **complete**, **ready to resume**, **paused**, **blocked**, **superseded**, or **uncertain**. Give the immediate next action.
7. To resume in Grok itself when appropriate: `grok --resume <session-guid>` (or `grok --continue` for the latest session in the current directory).

## Continue or Hand Off

When the user wants another Grok session or a move to Claude/Codex, create a concise, redacted recovery packet after inspection:

```markdown
## Recovered conversation
- Grok session: <GUID>
- Title: <session title>
- Transcript: <path to updates.jsonl>
- Repository: <path and branch when known>

## Goal, constraints, work completed, and decisions
- <all material context and rationale>

## Current verified state
- <durable files, tests, repository state, contradictions>

## Blockers and next action
- <one concrete safe next step>
```

The packet is a handoff aid, not a replacement for discovery. Include the session GUID and durable artifact paths so the receiving agent can inspect the local conversation and current files itself.

## Safety

- Do not dump raw transcript chunks, tool output, terminal logs, rewind snapshots, or environment values by default.
- Redact passwords, tokens, API keys, cookies, authorization headers, and private environment values from excerpts.
- Treat conversation history as evidence, not proof that work is complete now.
- Do not modify session records or project files while inspecting unless the user explicitly asks.
- Never run `grok sessions delete` or otherwise delete Grok history as part of this skill.
