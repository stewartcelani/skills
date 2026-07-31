---
name: spec-herdr-review
description: Run visible multi-agent spec reviews in Herdr through interactive agent CLIs such as Claude, Codex, Copilot/GLM, or Grok/Composer. Supports two modes — a spec review (the design, before implementation) and an implementation review (the implemented diff vs the spec, after the calling model has built it). Ask for reviewers first if none are specified. Requires HERDR_ENV=1.
---

# Spec Herdr Review

Use this skill to ask one or more external agent CLIs for a review from visible Herdr panes in a per-project reviews workspace, separate from the dev-server and working workspaces.

This skill drives **interactive agent CLIs through Herdr's agent surface**, not headless prompt mode. Herdr starts the real CLI UI in a pane, `herdr agent prompt` submits the instruction, and Herdr's lifecycle states tell you when each reviewer is finished.

Read the `herdr` skill first if you are not already fluent in the CLI. This skill covers the review workflow; `herdr` covers the command surface, ID rules, and safety rules.

## Preflight

Herdr is required. Verify you are inside a Herdr-managed pane before doing anything else:

```bash
test "${HERDR_ENV:-}" = 1
```

If the check fails, say you are not running inside Herdr and stop. Do not fall back to another multiplexer.

## Two Review Modes

This skill runs in one of two modes. **Decide the mode before doing anything else**, because it changes the filenames, what the request file points the reviewer at, and what the reviewer is allowed to read/run.

### Mode A — Spec review (BEFORE implementation)

Review the **design itself**, verified against the **existing codebase**. The reviewer judges whether the plan is correct, complete, and safe to build — and a core part of that is **reading the current code to confirm the spec's claims are true**: that the files, line references, integration points, current behaviors, and assumptions the spec cites actually match the codebase. The difference from Mode B is only that there is no *new implementation diff* yet — not that the reviewer ignores code.

- Trigger phrases: "review the spec", "review this spec", "review the design", "before I implement", "is this spec ready", "second pair of eyes on the spec".
- Scope given to reviewers: `SPEC.md`, `plan.md`, `mockups.md`, `findings.md` and any prior decisions/review responses, PLUS the existing codebase the spec references. The reviewer must open the cited files and verify the spec describes them accurately, flag stale/incorrect/missing claims, and judge feasibility against what is really there. There is no new diff to review — the "code" here is the current state the spec builds on.
- Filenames: `REQUEST_FOR_REVIEW_{SUFFIX}.md` / `REQUEST_FOR_REVIEW_RESPONSE_{SUFFIX}.md`.
- Tab label inside the reviews workspace: `spec-review-{feature}`.
- Reviewers must not edit anything; they read the spec and the existing code, then report design gaps, risks, and any place the spec misrepresents the codebase before implementation starts.

### Mode B — Implementation review (AFTER implementation)

Review the **implemented work** that the calling model has already written against the spec. The reviewer reads the actual diff and judges whether the implementation correctly and safely satisfies the spec.

- Trigger phrases: "review the implementation", "review what you built", "review the implemented work", "after implementing", "review my changes against the spec", "implementation review".
- Scope given to reviewers: the spec files PLUS the implemented change set. The request file must point reviewers at `git status` + `git diff` (or an explicit changed-file list), the invariants that must still hold, and a short summary of what was built and which gates already pass.
- Filenames: `REQUEST_FOR_IMPLEMENTATION_REVIEW_{SUFFIX}.md` / `REQUEST_FOR_IMPLEMENTATION_REVIEW_RESPONSE_{SUFFIX}.md`.
- Tab label inside the reviews workspace: `impl-review-{feature}`.
- Reviewers may read code and run read-only gates (build, tests) but must **not** edit product code.

If the user's request does not make the mode obvious, ask which mode they want before creating artifacts. When in doubt: "before implementation" = Mode A, "of the implemented work / of what was built" = Mode B.

## Required Inputs

Before starting, identify:

- Review mode (Mode A spec review or Mode B implementation review — see above).
- Spec directory, usually `spec/{feature}/`.
- Reviewer/model list.
- Request file path per reviewer — `REQUEST_FOR_REVIEW_{REVIEWER}.md` (Mode A) or `REQUEST_FOR_IMPLEMENTATION_REVIEW_{REVIEWER}.md` (Mode B).
- Response file path per reviewer — the matching `..._RESPONSE_{REVIEWER}.md`.

The request and response files are required review artifacts, not optional references. Do not start reviewer agents until every requested reviewer has a reviewer-specific request file and response file scaffold on disk.

If the user does **not** specify reviewers/models, stop and ask exactly which reviewers to use, offering the aliases from the map below. Do not guess default reviewers.

## Reviewer Alias Map

Normalize requested reviewers case-insensitively. Herdr agent names must match `[a-z][a-z0-9_-]{0,31}` and be unique among live agents, so prefix them with `rv-`.

Every reviewer runs as a **100% interactive CLI** in a visible pane. There is no headless path in this skill (see *Start The Reviewer Agents*).

### USER: define your own reviewers here

The names a user says out loud rarely match the Herdr `--kind` of the CLI that actually runs — e.g. someone says "GLM" but the installed CLI is `copilot`, or says "Composer" but the CLI is `grok`. Fill in your own mapping so this skill resolves your vocabulary to real installed CLIs. Delete rows you do not have.

| User says | Herdr `--kind` (installed CLI) | Agent name | Request suffix | Launch flags (after `--`) |
|---|---|---|---|---|
| `Claude`, `claude` | `claude` | `rv-claude` | `CLAUDE` | `--add-dir "$(dirname "$spec_backing_path")"` |
| `Codex`, `codex` | `codex` | `rv-codex` | `CODEX` | *(none)* |
| `GLM`, `glm`, `copilot` | `copilot` | `rv-glm` | `GLM` | `--allow-all-tools --allow-all-paths --no-ask-user` |
| `Composer`, `Grok`, `grok` | `grok` | `rv-grok` | `GROK` | `--no-memory --no-subagents` |
| *(add your own)* | | | | |

Rules for the map:

- **User says** — whatever the user actually calls it, including brand/model nicknames that differ from the binary.
- **Herdr `--kind`** — the CLI kind Herdr recognizes. Confirm it exists in this install with `herdr agent start --help`, which prints the supported kind list.
- **Agent name** — `rv-{alias}`, lowercase, unique among live agents.
- **Request suffix** — stable, uppercase, filesystem-safe; used in the artifact filenames.
- **Launch flags** — only flags that keep the CLI interactive while removing interruptions (path grants, tool auto-approval, memory off). Never a headless/print flag.

If the user names a reviewer outside the map and Herdr supports its kind, use that kind with an `rv-{alias}` name and an uppercase sanitized suffix. If Herdr does not support the kind, say so and ask how to proceed; do not start it as a raw pane process and pretend it is a managed reviewer.

If an `rv-*` name is already live from an earlier run, either reuse that reviewer deliberately or pick a suffixed name such as `rv-claude-2`. Check first:

```bash
herdr agent list
```

## Required Review Artifacts

Before creating any Herdr layout, create or refresh one request file and one response file per reviewer. Each reviewer gets a standalone, self-contained prompt file that can be understood without chat history, plus a dedicated response file where the CLI must write its output.

Default filenames:

- Normal spec review: `spec/{feature}/REQUEST_FOR_REVIEW_{SUFFIX}.md` and `spec/{feature}/REQUEST_FOR_REVIEW_RESPONSE_{SUFFIX}.md`.
- Implementation-vs-spec review: `spec/{feature}/REQUEST_FOR_IMPLEMENTATION_REVIEW_{SUFFIX}.md` and `spec/{feature}/REQUEST_FOR_IMPLEMENTATION_REVIEW_RESPONSE_{SUFFIX}.md`.

Use the reviewer's stable uppercase suffix from the map. If the user supplies custom model names, make the suffix obvious and filesystem-safe.

Each request file must include:

- Reviewer/model name and the Herdr agent kind it will run as.
- The active spec directory and the user goal being reviewed.
- The exact review scope, stated as the mode: **Mode A spec review** (judge the design before code) or **Mode B implementation review** (judge the implemented diff against the spec). Say which one explicitly so the reviewer does not guess.
- Relevant files to read: the spec files always; for Mode B also the new/changed source and test files.
- Constraints and invariants the reviewer must preserve — the domain rules that must not be broken by this change (billing/pricing rules, data-retention rules, auth boundaries, migration ordering, and so on).
- Known decisions or open questions the reviewer should not rediscover from chat.
- Exact instructions for writing the response to that reviewer's response file.
- Expected response sections: blocking issues, non-blocking concerns, missing tests/proof, suggested edits, final recommendation.
- An explicit completion-signal instruction: after the reviewer has written/replaced its response file, its final chat message must be `DONE.` on its own line (nothing else on that line). Herdr's lifecycle state is the primary completion signal, but this marker makes `herdr agent read` unambiguous about whether the reviewer finished or bailed.

**Mode A (spec review) request files additionally state:** there is no new diff yet — review the design for correctness, completeness, risk, and testability, AND verify the spec against the existing codebase. The reviewer must open the files/line references the spec cites, confirm the described current behavior and integration points are accurate, and flag any stale, wrong, or missing claims. List the key existing files the spec depends on so the reviewer knows where to look. No code is being changed.

**Mode B (implementation review) request files additionally include:**

- An explicit instruction to run `git status` and `git diff` to see the change set (and/or an enumerated list of new/changed files).
- A short "what was built" status summary: the new components, how they wire in, and which gates already pass.
- The read-only gate commands the reviewer may run to verify (the project's build and focused test commands), with a clear "do not edit product code" boundary.
- Specific things to check (e.g. did a refactor lose a needed boundary, can stale/terminal states still publish out of order, does anything touch money/permissions/data-loss paths, are the tests meaningful or trivially green).
- A recommendation vocabulary for the final section: **ship / ship-with-fixes / do-not-ship**.

Each response file must be created before launch with a small pending scaffold:

- Reviewer/model name.
- Request file path.
- Status: pending.
- Expected output sections.
- A clear instruction that the reviewer should replace or fill the file with its final review.
- A reminder that once the file is saved, the reviewer's final chat message must be `DONE.` on its own line.

If a request file already exists, read it before reuse. Reuse it only when it matches the current reviewer, spec, and requested scope; otherwise refresh it. For multiple reviewers, do not reuse one generic request file unless the user explicitly asks for a shared request.

After writing artifacts, verify their paths before creating panes, for example with `ls -la spec/{feature}/REQUEST_FOR_*`.

## First Checks

Confirm the review mode (A or B). Read the active spec files enough to understand the packet; for Mode B also skim `git status`/`git diff` so the request file can point reviewers at the real change set. Request and response artifacts are mandatory: create or refresh them using `Required Review Artifacts` before creating Herdr layout.

Resolve the repository before creating layout. Review panes must live in the project's reviews workspace, never in a dev-server workspace or the user's working tab.

```bash
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
test -d "$repo_root/spec" || { echo "No repo-root spec/ directory: $repo_root" >&2; exit 1; }
spec_backing_path="$(realpath "$repo_root/spec")"
```

`spec/` is often a symlink into a notes vault (Obsidian or similar), so resolve it — reviewers that sandbox by path need the backing location, not the symlink.

## The Reviews Workspace

Each project gets one persistent reviews workspace, and it is **always** labelled `{Project}: Reviews`. This matches the `{Project}: Dev` / `{Project}: Servers` convention, so the reviews workspace is instantly recognizable in `herdr workspace list`.

Derive `{Project}` from the repository, in title case:

```bash
project_name="$(basename "$repo_root")"
# If the repo root is a generic checkout dir (repo, src, main, code, trunk),
# use its parent instead — /opt/myapp/repo -> "Myapp", not "Repo".
case "$project_name" in
  repo|src|main|code|trunk) project_name="$(basename "$(dirname "$repo_root")")" ;;
esac
project_title="$(printf '%s' "$project_name" | sed -E 's/[-_]+/ /g; s/\b(.)/\u\1/g')"
review_ws_label="$project_title: Reviews"

herdr workspace list
```

<!-- USER: if a repo should use a specific project title, pin it here instead of
     relying on the basename, e.g.
     case "$repo_root" in
       /path/to/project-a) review_ws_label="Project A: Reviews" ;;
     esac
-->

Read the workspace ID for `$review_ws_label` out of that JSON. If it is absent, create it without stealing focus:

```bash
herdr workspace create --label "$review_ws_label" --cwd "$repo_root" --no-focus
```

Use `.result.workspace.workspace_id` and `.result.root_pane.pane_id` from the response. A fresh workspace already has one tab and one root pane — use them for the first review run instead of creating a second tab.

Never repurpose `{Project}: Dev` or `{Project}: Servers` for reviewers. Never close a workspace you did not create.

## Create The Review Tab

Create one tab per review run inside the reviews workspace, labelled for the mode and feature:

```bash
# Mode A
herdr tab create --workspace "$review_ws" --label "spec-review-{feature}" --cwd "$repo_root" --no-focus
# Mode B
herdr tab create --workspace "$review_ws" --label "impl-review-{feature}" --cwd "$repo_root" --no-focus
```

Read `.result.tab.tab_id` and `.result.root_pane.pane_id` from the response. Keep labels short; truncate long feature names rather than wrapping the tab bar.

If a tab with that exact label already exists from an earlier run, either reuse it (only when the same reviewers should be re-run on the same packet) or create `spec-review-{feature}-2`. Do not take over panes that still contain an active agent.

Create one pane per reviewer. The tab's root pane hosts the first reviewer; split for each additional one. Split a wide pane right and a narrow or tall pane down, and check geometry rather than guessing:

```bash
herdr pane layout --pane "$root_pane"
herdr pane split --pane "$root_pane" --direction right --cwd "$repo_root" --no-focus
```

Read each new pane ID from `.result.pane.pane_id`. Avoid repeated same-direction splits that leave unusably narrow columns — for three or four reviewers, split right once, then split each column down. Verify the layout before starting agents:

```bash
herdr pane list --workspace "$review_ws"
```

## Start The Reviewer Agents

Each pane must be at an interactive shell prompt. Start the real CLI through Herdr's agent surface so lifecycle states work, and pass native CLI arguments only after `--`.

Reviewers run **100% interactively**. Do **not** use headless options such as `-p`, `--prompt`, `--prompt-file`, `--print`, or equivalent. A headless invocation is an ordinary pane process, so `agent start`, `agent prompt`, `agent wait`, and the whole lifecycle surface stop working — and the user cannot watch the review happen.

Launch each reviewer with the kind and flags from your alias map:

```bash
herdr agent start rv-claude --kind claude --pane "$pane_claude" -- \
  --add-dir "$(dirname "$spec_backing_path")"

herdr agent start rv-codex --kind codex --pane "$pane_codex"

herdr agent start rv-glm --kind copilot --pane "$pane_glm" -- \
  --allow-all-tools --allow-all-paths --no-ask-user

herdr agent start rv-grok --kind grok --pane "$pane_grok" -- \
  --no-memory --no-subagents
```

`agent start` returns only once Herdr has detected that agent in the same pane and considers it ready for input, so there is no prompt-readiness polling to write. It defaults to a 30-second startup timeout; raise `--timeout` for a slow CLI rather than retrying blindly.

If a CLI rejects a flag, drop the unsupported flag and restart that agent rather than looping. Common cases:

- Reasoning-effort and model-selection flags are the usual offenders; some CLIs reject them per model or per account.
- If a server rejects an explicit model id ("unknown model id"), that model has not rolled out to this account — restart without the flag and record the fallback model in the synthesis.

Whenever a requested model or flag did not actually apply, say so when reporting results. Do not let the user believe a reviewer ran on a model it did not run on.

## Submit The Review Instructions

Send a short instruction that references files instead of embedding the whole spec. Submit to every reviewer first, then wait — otherwise reviewers run one at a time.

Template (Mode A — spec review):

```text
Read {REQUEST_FILE} and perform that review. Do not edit product code. Save your final answer to {RESPONSE_FILE}, replacing the file, with the requested sections. When done, your final message must be `DONE.` on its own line.
```

Template (Mode B — implementation review): explicitly tell the reviewer to inspect the diff.

```text
Read {REQUEST_FILE} and perform that implementation-vs-spec review. Use git status and git diff to see the change set. Do not edit product code. Save your final answer to {RESPONSE_FILE}, replacing the file, with the requested sections. When done, your final message must be `DONE.` on its own line.
```

Fan the prompts out without `--wait` so submission is not serialized:

```bash
herdr agent prompt rv-claude 'Read spec/{feature}/REQUEST_FOR_REVIEW_CLAUDE.md and perform that review. Do not edit product code. Save your final answer to spec/{feature}/REQUEST_FOR_REVIEW_RESPONSE_CLAUDE.md, replacing the file, with the requested sections. When done, your final message must be `DONE.` on its own line.'
herdr agent prompt rv-codex '...'
herdr agent prompt rv-glm '...'
```

`agent prompt` atomically submits the text and Enter while honoring the pane's live bracketed-paste mode, so there is no stray-Enter recovery step. If a submission returns an error, read the pane before resending — do not blind-retry into a CLI that may already hold the text.

For a single reviewer, `--wait --timeout <ms>` in one call is fine and adds Herdr's stall detection.

## Wait For Completion

Wait on lifecycle state per reviewer rather than scraping panes. Give real reviews a generous timeout:

```bash
herdr agent wait rv-claude --timeout 1800000
herdr agent wait rv-codex --timeout 1800000
herdr agent wait rv-glm --timeout 1800000
```

Without `--until`, this settles on `idle`, `done`, or `blocked`. Treat each outcome differently:

- `idle`/`done` — the reviewer stopped. Confirm the work actually landed before believing it.
- `blocked` — Herdr recognized an approval or question UI. Read the pane, answer or approve, then wait again. Do not assume it failed.
- `unknown` — an agent is present but unclassified. This is not proof of completion; read the pane.

Confirm each finished reviewer wrote a real review:

```bash
wc -c spec/{feature}/REQUEST_FOR_*REVIEW_RESPONSE_*.md
herdr agent get rv-claude
herdr agent read rv-claude --source recent-unwrapped --lines 120
```

A settled state plus a non-empty replaced response file plus a trailing `DONE.` is a finished review. A settled state with an untouched scaffold file means the reviewer bailed — read the pane and decide whether to re-prompt or report the failure.

Do not do deep synthesis while waiting.

Common failure to watch for: a CLI that cannot read `spec/` because it resolves into a vault path outside its sandbox. Restart that agent with the correct path grant (for example `--add-dir` for Claude or `--allow-all-paths` for copilot), or tell it to read through the repo path.

## Completion

When all requested reviewers are done:

1. Verify every per-reviewer request file exists and every response file exists and is non-empty.
2. Do a light glance for obvious failure text such as "cannot access", "permission denied", or an empty response.
3. Tell the user the reviews workspace label, tab label, pane IDs, and agent names used, plus which response files were written.
4. Do not deeply analyze the reviews unless the user asks.

## Clean Up The Tab

Reviewer panes are disposable; the response files are the durable artifact. Once the reviews are captured and the user has what they need, close the review tab so the reviews workspace does not silt up:

```bash
herdr tab close "$review_tab"
```

Rules for cleanup:

- Close only the tab this run created, by its ID from `tab create`.
- Never close the reviews workspace itself — it is meant to persist and be reused.
- Never close a tab that still holds a `working` or `blocked` agent. Check `herdr agent list` first.
- Do not close a tab while the user may still want to read the pane, for example when a reviewer failed and the scrollback is the only evidence. Say the tab was left open and why.
- If the user asks to keep reviewers alive for follow-up questions, leave the tab and say so. Offer to close it later.
- On a later run, if `herdr tab list --workspace "$review_ws"` shows stale review tabs from finished runs, mention them and offer to close them. Do not close another agent's tabs unprompted.

## Safety

- Do not deploy or publish.
- Do not let reviewer CLIs edit product code unless the user explicitly asks for implementation.
- Keep reviewers out of `{Project}: Dev` and `{Project}: Servers`. Never restart a dev server from this skill.
- Use `--no-focus` throughout; the user's focus stays where they left it.
- Target panes and agents by ID or unique name, never by another client's focused pane.
- Parse IDs out of Herdr's JSON responses; never derive them from sidebar order or from the examples above.
- Do not close workspaces, tabs, panes, or agents you did not create, beyond the cleanup rules above.
- Keep important results in spec response files, not only in pane scrollback — panes running agents on the alternate screen lose rows that never reach Herdr's scrollback.
