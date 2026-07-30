---
name: claude-session
description: Find and inspect local Claude Code conversations by session GUID, title, phrase, or recent activity. Use when the user runs `/claude-session`, asks what Claude Code work they have been doing lately, says a Claude Code conversation died, ran out of context, crashed, or exhausted usage, wants to resume a named conversation, or wants to continue it in Claude or Codex.
---

# Claude Session

Find persisted local Claude Code conversations on the current machine, inspect what happened, and recover the work. A handoff to a new Claude conversation or Codex is an optional use after the conversation is found and understood.

## What to Use

```text
/claude-session              What have I been working on lately? List recent local conversations.
/claude-session <GUID>       Inspect one known Claude Code conversation.
/claude-session latest       Inspect the most recent local conversation.
/claude-session "Blah Blah" Find a conversation by title or a remembered phrase.
```

Use this when a prior Claude Code conversation died from context exhaustion, a crash, login or usage trouble, or an interrupted session. Its local transcript can still reveal the user intent, work completed, decisions, errors, referenced files, and last next step.

## Scope

- Read Claude Code records stored in the current user's `.claude` directory: project transcripts, session metadata, history, and subagent files.
- Work on Windows, macOS, and Linux. Resolve the default local directory from the current user's home directory, or pass `--claude-home` for a copied or mounted store.
- Read a Desktop-driven remote conversation only if it was persisted by Claude Code in the same store.
- Do not claim to read ordinary local Claude Desktop chat history; that is a separate application store and is not supported yet.

## Local Discovery Workflow

```text
[recent | GUID | title | phrase]
                  |
                  v
[Local Claude Code session store]
                  |
                  v
[Inspect selected transcript + current project state]
                  |
                  v
[Resume here | start a new Claude conversation | continue in Codex]
```

Use `<python>` for an available Python 3 launcher and `<skill-dir>` for this skill's directory.

```text
# Recent conversations for every project or just this project.
<python> "<skill-dir>/scripts/claude_sessions.py" monitor --recent 8 --details
<python> "<skill-dir>/scripts/claude_sessions.py" monitor --cwd "<project-root>" --recent 8 --details

# Find by visible title or a distinctive remembered phrase.
<python> "<skill-dir>/scripts/claude_sessions.py" monitor --title "Blah Blah" --recent 8 --details
<python> "<skill-dir>/scripts/claude_sessions.py" monitor --query "distinctive phrase" --recent 8 --details

# Inspect a known session GUID.
<python> "<skill-dir>/scripts/claude_sessions.py" inspect <session-guid>
```

For a copied, mounted, or remote-accessible Claude Code store, add `--claude-home "<path-to-.claude>"` before the command.

## Inspect and Recover

1. With no identifier, list recent conversations and present the likely matches. Ask which one to inspect if the user has not identified it.
2. Use the GUID directly when supplied. Otherwise filter by title or search a distinctive remembered phrase.
3. Read the conversation summary: title, user requests, latest assistant message, recent tools, working directory, branch, referenced artifacts, and subagent count.
4. Read the current project state directly: repository status, recent history, specifications, plans, progress/readiness documents, changed files, and relevant test or build evidence.
5. If the old conversation and current files disagree, explain the difference and trust current durable project state.
6. Report the current status: **complete**, **ready to resume**, **paused**, **blocked**, **superseded**, or **uncertain**. Give the immediate next action.

## Continue or Hand Off

When the user wants to use another Claude conversation or move to Codex, create a concise, redacted recovery packet after inspection:

```markdown
## Recovered conversation
- Claude Code session: <GUID>
- Title: <conversation title>
- Transcript: <path>
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

- Do not dump raw transcript chunks, tool output, or environment values by default.
- Redact passwords, tokens, API keys, cookies, authorization headers, and private environment values from excerpts.
- Treat conversation history as evidence, not proof that work is complete now.
- Do not modify session records or project files while inspecting unless the user explicitly asks.
