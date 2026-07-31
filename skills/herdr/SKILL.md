---
name: herdr
description: "Control Herdr, a terminal multiplexer for coding agents, via the herdr CLI. Works from inside a Herdr pane and from outside (SSH, Claude Desktop, Cursor, ChatGPT, local shells) as long as the CLI can reach the Herdr session. Use when the user mentions Herdr or asks to inspect/control panes, tabs, workspaces, commands, or another agent. Do not use merely because a task could benefit from a background terminal, delegation, or parallel work."
---

# Herdr

Herdr organizes terminals into workspaces, tabs, and panes, recognizes coding agents running inside panes, and exposes the session through the `herdr` CLI.

## Inside and outside are both valid

**Use the CLI whenever it can talk to the session.** You do not need to be running inside a Herdr-managed pane.

Supported control paths include:

- An agent already inside a Herdr pane
- A shell or agent on the same machine that has `herdr` in `PATH` and can reach the session socket
- Remote clients over SSH (home PC, Claude Desktop, Cursor, ChatGPT, etc.) driving Herdr on the server

External control is intentional: it is how remote agents manage workspaces, servers, and sibling agents without falling back to raw tmux. **Never refuse Herdr work because you are "outside" Herdr or because `HERDR_ENV` is unset.**

The `herdr` binary talks to the reachable session. Use it to inspect neighboring work, create terminal layout, start agents and commands, read output, and wait for state changes.

Only report that Herdr is unavailable if the CLI itself fails to reach a session (connection refused, no server, socket missing). Empty env or an external client is not a failure.

## Caller context env vars (optional convenience)

When a process *is* inside a managed pane, Herdr *may* inject:

```bash
printf '%s\n' "${HERDR_ENV:-}" "$HERDR_WORKSPACE_ID" "$HERDR_TAB_ID" "$HERDR_PANE_ID"
```

- `HERDR_ENV=1` means this process was launched inside a Herdr-managed pane (when injection worked).
- `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, and `HERDR_PANE_ID` identify that pane when present.

Injection is unreliable: nested shells, agent runtimes, IDE terminals, SSH sessions, and many launch paths drop these vars. Missing env is normal for external control and is also common inside Herdr.

When env is present, prefer it (`--current`, `$HERDR_PANE_ID`, `$HERDR_WORKSPACE_ID`). When it is missing — the default for external/SSH clients — discover live state and target explicitly:

```bash
herdr workspace list
herdr pane list
herdr agent list
herdr pane current --current   # may fail outside a pane; then use explicit ids from list
```

## Project-specific Herdr setups

Some repositories keep a standing Herdr workspace with its own layout, launch commands, and gotchas — one tab per dev server, a required start order, a shared backend port, and so on. That belongs in a **separate per-project skill**, not here. This skill covers the CLI surface, ID rules, and safety rules; the project skill covers one repository.

Before driving Herdr inside a repository, check whether such a skill exists (a name like `herdr-{project}` is the usual convention) and read it first. If none exists, discover live state with `herdr workspace list` / `herdr tab list` / `herdr pane list` and ask the user which workspace to use rather than inventing layout.

<!-- USER: fill this in for your own machine, or delete it. One row per repository
     that has a standing Herdr workspace and a companion skill.

| Repository root      | Companion skill  | What that workspace holds                          |
|----------------------|------------------|----------------------------------------------------|
| /path/to/project-a   | `herdr-project-a`| `Project A: Servers` — one tab per dev site, ports  |
| /path/to/project-b   | `herdr-project-b`| API must start before web; mobile bundler tab       |
-->

Naming convention worth keeping: label workspaces `{Project}: Dev`, `{Project}: Servers`, and `{Project}: Reviews`, so the purpose of a workspace is obvious from `herdr workspace list`.

## Learn the current CLI

The installed binary is the authority for command syntax. Start with:

```bash
herdr --help
```

Then print the relevant command group by running the group without a subcommand:

```bash
herdr agent
herdr pane
herdr workspace
herdr tab
herdr worktree
herdr terminal
herdr notification
herdr integration
herdr session
```

Do not run bare `herdr` for discovery; it launches or attaches the TUI. Do not probe a mutating nested command by omitting arguments. Commands such as `herdr workspace create` are valid with defaults and will execute.

Most control commands return JSON. Read identifiers and state from those responses instead of predicting them.

## Understand layout, panes, and agents

Choose the primitive that matches the job:

- Workspace, tab, and pane topology organize terminal locations.
- Pane commands control raw terminals, shells, tests, servers, input, and output.
- Agent commands control the recognized coding agent currently occupying a pane.

A pane exists whether or not it contains an agent. `agent start` requires an existing available shell pane and never creates, splits, or moves layout. Use pane commands for ordinary processes. Use agent commands when Herdr must validate agent identity or interpret `idle`, `working`, `blocked`, `done`, and `unknown` lifecycle states.

Agent commands accept either a unique live agent name or the pane ID currently hosting that agent. They do not accept terminal IDs or bare agent-kind labels. Names must match `[a-z][a-z0-9_-]{0,31}` and be unique among live agents. A name follows the current pane occupant and is cleared when that agent exits, is released, or is replaced.

Agents a user launched by hand (typing the CLI into a pane) are recognized but **unnamed**: they appear in `agent list` without a name field, so parse those entries defensively. Drive an unnamed agent by its pane ID — `herdr agent prompt <pane-id> "..."` works and is the normal way to brief an agent you did not start.

`idle` means the agent is ready for input and its tab has been seen in the focused Herdr UI. `done` is the same underlying idle state after unseen background work finishes. Focusing the tab or targeting the pane or agent with a focus command marks it seen. CLI reads do not mark it seen. `blocked` means Herdr recognized an approval or question UI. `unknown` means an agent is present but Herdr cannot classify it confidently; it does not prove completion.

**A settled state is a hint, not proof of completion.** Agent CLIs briefly read as `idle` between internal steps, and some run sub-modes (sub-agent swarms, background tool phases, long spinners) that classify as settled while the pane visibly says it is still working. The reverse also happens: a pane's rendered spinner can outlive the state change. Before acting on `idle`/`done`, confirm against evidence — `agent read` shows the final message, or the artifact the agent was told to produce exists. Never conclude an agent bailed from state alone; never re-prompt into a pane you have not read.

## Use IDs and caller context

Public IDs are opaque stable handles:

- workspace: `w1`
- tab: `w1:t1`
- pane: `w1:p1`

Closed tab and pane IDs are not reused. A pane moved into another workspace receives a new workspace-qualified pane ID. After `pane move`, continue with `.result.move_result.pane.pane_id` or the live agent name. The old value is reported as `.result.move_result.previous_pane_id`; only the moved process's inherited caller context keeps resolving that old ID, so do not use it as a general agent target.

Prefer `--current` only when you are the calling pane and caller context is available. External or SSH clients usually have no caller pane — use explicit workspace/tab/pane ids or agent names from list responses. Omitting a target may use the UI-focused pane, which can belong to the user or another client; that is fine when intentional, but prefer explicit ids for automation.

Discover live state with (scope by `$HERDR_WORKSPACE_ID` only when it is set):

```bash
herdr workspace list
herdr tab list --workspace "$HERDR_WORKSPACE_ID"   # if set; otherwise list after picking a workspace id
herdr pane current --current                        # optional; often N/A from outside
herdr pane list --workspace "$HERDR_WORKSPACE_ID"   # if set; otherwise use an id from workspace list
herdr agent list
```

Creation responses expose the IDs to use next. `workspace create` returns `.result.workspace`, `.result.tab`, and `.result.root_pane`. `tab create` returns `.result.tab` and `.result.root_pane`. `pane split` returns the new pane as `.result.pane`.

## Start and coordinate an agent

When you have a calling pane (inside Herdr with context), default to a sibling pane in that tab and the current working directory. From outside, pick the workspace/tab/pane the user named, or the obvious project workspace from `workspace list` / a project-specific skill. Do not create a workspace, tab, worktree, or different cwd unless the user explicitly requests that topology or location.

Honor a direction requested by the user. When you know the target pane id (from `$HERDR_PANE_ID`, `herdr pane current --current`, or list/discovery):

```bash
herdr pane layout --pane <pane-id>
```

Split a wide pane to the right and a narrow or tall pane down. Avoid repeated same-direction splits that create unusably narrow columns or short rows. Prefer `--no-focus` for background work. Preserve a sensible working directory with `--cwd` (caller `$PWD` when inside; an explicit project path when controlling from outside):

```bash
# inside, with caller context
herdr pane split --current --direction right --cwd "$PWD" --no-focus

# outside / SSH / missing env — always use explicit pane id
herdr pane split --pane <pane-id> --direction right --cwd /path/to/project --no-focus
```

Replace `right` with `down` when appropriate. Read the new pane ID from `.result.pane.pane_id`.

An available shell pane must be at its interactive prompt, with the shell itself in the foreground and no foreground command, editor, or agent running. Start a supported agent in that pane with a useful unique name:

```bash
herdr agent start reviewer --kind codex --pane <returned-pane-id>
```

Use the kind requested by the user. Run `herdr agent` to inspect the installed kind list and options. Pass native agent arguments only after `--`:

```bash
herdr agent start reviewer --kind codex --pane <returned-pane-id> -- <agent-args...>
```

`agent start` returns only after Herdr detects the expected agent in the same pane and considers it ready for interactive input. It defaults to a 30-second startup timeout.

Submit work through the agent surface:

```bash
herdr agent prompt reviewer "Review the current diff and report only actionable findings." --wait --timeout 120000
```

`agent prompt` atomically submits text and encoded Enter while honoring the pane's live bracketed-paste mode. For normal agent work, `--wait` is enough: it waits for the first settled `idle`, `done`, or `blocked` state. Do not repeat those defaults with `--until`.

A prompt sent from a non-working state must produce an observed lifecycle change within five seconds. Otherwise Herdr returns `agent_prompt_stalled` instead of waiting indefinitely. This wait tracks lifecycle state, not an individual turn; if the agent is already working, completion of the active turn may satisfy it.

Use `--until` only for a state-specific workflow, such as waiting for an already-running agent to request input:

```bash
herdr agent wait reviewer --until blocked --timeout 120000
```

Without `--until`, standalone `agent wait` uses the same settled-state defaults as `agent prompt --wait`.

Use logical keys for interactive agent UI controls:

```bash
herdr agent send-keys reviewer esc
herdr agent send-keys reviewer ctrl+c
```

Herdr validates all keys before writing any bytes. Read the result through the resolved agent:

```bash
herdr agent get reviewer
herdr agent read reviewer --source recent-unwrapped --lines 120
```

If a wait fails or returns `blocked`, inspect `agent get` and `agent read` before deciding what input to send. Use the pane surface only when raw terminal control is intentional.

## Run an ordinary command in another pane

Create a sibling pane with the same geometry rule, preserve cwd, and keep user focus unchanged. Use `--current` only when caller context exists; otherwise split with `--pane <id>`:

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
# or: herdr pane split --pane <pane-id> --direction right --cwd /path/to/project --no-focus
```

Read the new pane ID from `.result.pane.pane_id`, then run and inspect the command:

```bash
herdr pane run <returned-pane-id> "just test"
herdr pane wait-output <returned-pane-id> --match "test result" --timeout 120000
herdr pane read <returned-pane-id> --source recent-unwrapped --lines 120
```

`pane run` atomically sends command text and Enter. `pane wait-output` searches the selected snapshot immediately, so output that already exists can match. Use `--match <text>` for a literal substring or `--regex <pattern>` for a Rust regular expression. Omitting `--timeout` allows an indefinite wait.

Use the read source that matches the task:

- `visible`: the currently rendered viewport.
- `recent`: recent rendered output, including soft wraps.
- `recent-unwrapped`: recent output with soft wraps joined; prefer it for logs and transcripts.
- `detection`: the plain-text bottom-buffer snapshot used for agent detection.

Use `--format ansi` when colors and terminal styling are evidence. Otherwise use text.

`--lines` asks Herdr for more rows from the pane's available screen and host scrollback. If increasing it does not reveal more of a completed response, the pane is probably running the agent on the terminal's alternate screen. Rows that leave the alternate screen do not enter Herdr's host scrollback, so a larger line count cannot recover them.

After that failed read, ask the agent to write its complete response as Markdown in a temporary directory and reply only with the file path, then read the file directly. Use this only as a fallback; do not request file output in the initial prompt.

## Delegating real work: patterns that survive contact

These rules come from long multi-agent driving sessions. They are what actually breaks.

**Completion = sentinel + artifact, never state alone.** When you brief an agent, tell it to (a) write its durable output to a named file and (b) end its final chat message with a fixed sentinel line (for example `DONE.` or `PACKET-DONE`) on its own line. Completion is then: settled state AND the sentinel visible in `agent read` AND the artifact non-empty. A settled state with an untouched artifact means the agent bailed — read the pane before re-prompting.

**Watchdog every long wait.** A deadlocked or wedged agent never notifies you. Do not rely on one unbounded `agent wait`. For anything long-running, poll on an interval in a loop with a hard iteration cap, checking both lifecycle state and the artifact, and bail out loudly on timeout with the last pane contents. Waits that a first watchdog declared dead have later completed — before declaring failure, read the pane: if the agent is visibly still producing, re-arm a longer watchdog instead of interrupting.

**Babysit approval-mode agents deliberately.** An agent running with permission prompts will go `blocked` mid-task. Read the pane and answer. If you automate approvals, whitelist narrowly (read-only commands, directory-read grants), approve only exact matches, and bail out loudly on anything unrecognized — never auto-approve writes, network sends, or commands you cannot classify. If a safety layer refuses a permissive launch flag, run the agent with prompts on and babysit; do not look for a bypass.

**Know your own pane.** Before driving another agent, know which pane you are (`$HERDR_PANE_ID` or `herdr pane current --current`) and verify the target is not you. Agents have typed briefs into their own pane and then monitored their own idle state as if it were the worker's. Always pass an explicit target for automation.

**Coordinate a shared worktree like it will burn you, because it will.** Multiple agents editing one checkout is workable but has sharp edges:

- Before starting an agent that edits files, run `git status` and note what is already dirty and whose it is. Give each agent an explicit file carve-out and tell it which dirty files belong to other lanes.
- When you commit one agent's packet out of a mixed tree, stage its exact file list — attribute every dirty file to a lane first (by diffing content, not by guessing), and leave other lanes' files uncommitted. Watch for shared files (a `package.json`, a barrel export) where one lane's commit can swallow another lane's hunk; if a swallow happens, close the gap in the very next commit.
- Sequence two lanes that need the same large file; do not let them interleave. The second lane starts when the first lane's commit lands.
- Never resolve collisions with git undo commands (`checkout --`, `reset`, `restore`) in a live multi-agent tree — revert surgically with file edits, or you will destroy a sibling's uncommitted work.

**Commands that need a real TTY get a pane.** Some CLIs (deploy tools, TUIs, anything that probes the terminal) crash or hang in headless exec environments. Run them with `pane run` in a real pane and watch for their success/failure markers with `pane wait-output` or a polling read. Poll for the marker of *this* run — a distinctive new line — not text that an earlier run already left in scrollback.

**Read before you write.** Before sending anything into a pane — prompt, keys, a command — read its recent output. Panes hold live state: a half-typed command, a running process, an approval prompt, another client's work. `agent prompt` refuses unsafe states, but `pane run` and `send-keys` trust you.

## Safety and coordination rules

- External and remote control are first-class. Do not require `HERDR_ENV=1` or refuse because the agent is outside Herdr.
- Use `--no-focus` for background work unless the user asked to switch context.
- Prefer an explicit pane ID or unique agent name. Use `--current` only when caller context is real. Do not rely on another client's focused pane for automation.
- Parse IDs from JSON responses. Do not derive them from sidebar order or examples.
- Do not close workspaces, tabs, panes, or sessions you did not create unless the user explicitly asked.
- Never run `herdr server stop` from an active session unless the user explicitly intends to stop the server and its pane processes.
- Never kill the main Herdr process. Use named test sessions for experiments that need an isolated server.
- CLI server errors are JSON on stderr with exit status 1. CLI syntax errors exit with status 2.
