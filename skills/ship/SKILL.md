---
name: ship
description: Stage, commit, and push every current Git repository change in one operation. Use when the user says `/ship`, “ship it”, “commit and push everything”, “stage everything”, “push everything”, or otherwise explicitly authorizes committing all current worktree changes without splitting or reviewing them individually.
---

# Ship

Ship every current Git-trackable worktree change in one commit and push the current branch. This is intentionally a YOLO workflow: the user's `/ship` request is explicit approval to include mixed, broad, messy, generated, unrelated-looking, staged, unstaged, untracked, and deleted changes together.

## Workflow

```text
/ship
  |
  v
[Inspect branch, upstream, and summary]
  |
  v
[Stage every Git-trackable change]
  |
  v
[One accurate commit]
  |
  v
[Push current branch]
```

1. Confirm the current repository, branch, upstream (if any), worktree summary, and recent commits.
2. Read enough of the visible change summary to write an accurate concise commit message. Do not spend time separating changes or deciding whether a file belongs.
3. Stage every Git-trackable change from the repository root with `git add -A`.
4. Commit all staged changes in one commit:
   - Subject: `<type>(<scope>): <concise description>`; 72 characters or fewer.
   - Body: briefly state what changed and why.
   - Use one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, or `chore`.
5. Push the current branch to its upstream. If no upstream exists, push with tracking to `origin`.
6. Report the commit hash, branch, and push result.

## Rules

- Treat `/ship` and equivalent wording as authorization to include every Git-trackable change. Do not ask whether to include untracked files or seemingly unrelated changes.
- Respect explicit user overrides for remote, branch, commit message, or skipping the push.
- Do not create an empty commit when the worktree is clean unless the user explicitly asks.
- Git-ignored files remain ignored; do not force-add them unless the user explicitly names them.
- If a commit hook fails, report the failure. Do not bypass it unless the user explicitly asks.
- If the push is rejected because the remote moved, stop and report it. Do not rebase, merge, force-push, or overwrite remote history unless the user explicitly asks.
- Do not open a pull request unless the user explicitly asks.

## Scope

This skill only relies on Git and works wherever Git is available. It does not assume a specific operating system, hosting provider, branch name, repository layout, or external integration.
