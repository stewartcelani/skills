#!/usr/bin/env python3
"""Monitor recent local Codex Desktop sessions and their durable spec state."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inspect_session import (
    find_transcripts,
    read_jsonl,
    summarize_transcript,
    truncate,
)


CODEX_HOME = Path.home() / ".codex"
STATE_DB = CODEX_HOME / "state_5.sqlite"
SESSION_INDEX = CODEX_HOME / "session_index.jsonl"


@dataclass(frozen=True)
class ThreadInfo:
    id: str
    title: str
    updated_at: int
    cwd: str
    archived: bool
    rollout_path: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    preview: str | None = None


def utc(ts: int | float | None) -> str:
    if not ts:
        return "?"
    return datetime.fromtimestamp(float(ts), timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def age_label(ts: int | float | None) -> str:
    if not ts:
        return "?"
    seconds = max(0, int(time.time() - float(ts)))
    if seconds < 90:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 90:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"


def normalise_cwd(value: str) -> str:
    """Make Codex's extended Windows paths comparable with ordinary paths."""
    path = value[4:] if value.startswith("\\\\?\\") else value
    return os.path.normcase(os.path.normpath(path))


def read_index_threads() -> list[ThreadInfo]:
    if not SESSION_INDEX.exists():
        return []

    latest: dict[str, dict[str, Any]] = {}
    for event in read_jsonl(SESSION_INDEX):
        session_id = event.get("id")
        if not isinstance(session_id, str):
            continue
        updated = parse_iso_timestamp(event.get("updated_at"))
        prior = latest.get(session_id)
        if prior is None or updated >= int(prior.get("_updated_at", 0)):
            latest[session_id] = {**event, "_updated_at": updated}

    return [
        ThreadInfo(
            id=session_id,
            title=str(entry.get("thread_name") or "(unnamed)"),
            updated_at=int(entry.get("_updated_at", 0)),
            cwd="",
            archived=False,
        )
        for session_id, entry in latest.items()
    ]


def parse_iso_timestamp(value: Any) -> int:
    if not isinstance(value, str) or not value:
        return 0
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def read_state_threads() -> list[ThreadInfo]:
    if not STATE_DB.exists():
        return []

    query = """
        select id, title, updated_at, updated_at_ms, cwd, archived, rollout_path,
               model, reasoning_effort, preview
        from threads
    """

    threads: list[ThreadInfo] = []
    try:
        connection = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        with connection:
            for row in connection.execute(query):
                updated_at = int(row["updated_at"] or 0)
                updated_ms = int(row["updated_at_ms"] or 0)
                if not updated_at and updated_ms:
                    updated_at = updated_ms // 1000
                threads.append(
                    ThreadInfo(
                        id=str(row["id"]),
                        title=str(row["title"] or "(unnamed)"),
                        updated_at=updated_at,
                        cwd=str(row["cwd"] or ""),
                        archived=bool(row["archived"]),
                        rollout_path=str(row["rollout_path"] or "") or None,
                        model=str(row["model"] or "") or None,
                        reasoning_effort=str(row["reasoning_effort"] or "") or None,
                        preview=str(row["preview"] or "") or None,
                    )
                )
    except sqlite3.Error:
        return []
    finally:
        try:
            connection.close()
        except Exception:
            pass

    return threads


def read_goals() -> dict[str, dict[str, Any]]:
    if not STATE_DB.exists():
        return {}

    goals: dict[str, dict[str, Any]] = {}
    try:
        connection = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        with connection:
            for row in connection.execute(
                "select thread_id, status, objective, tokens_used, updated_at_ms from thread_goals"
            ):
                goals[str(row["thread_id"])] = {
                    "status": row["status"],
                    "objective": row["objective"],
                    "tokens_used": row["tokens_used"],
                    "updated_at": int(row["updated_at_ms"] or 0) // 1000,
                }
    except sqlite3.Error:
        return {}
    finally:
        try:
            connection.close()
        except Exception:
            pass

    return goals


def newest_transcript(thread: ThreadInfo) -> Path | None:
    candidates: list[Path] = []
    if thread.rollout_path:
        path = Path(thread.rollout_path)
        if path.exists():
            candidates.append(path)
    candidates.extend(find_transcripts(thread.id))
    existing = [path for path in set(candidates) if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def spec_root(ref: str) -> str | None:
    parts = ref.split("/")
    if len(parts) < 2:
        return None
    if parts[0] not in {"spec", "spec-archive"}:
        return None
    if parts[1] in {"...", "OWNER", "SKILL.md", "orientation", "packet", "plan"}:
        return None
    if "]" in parts[1]:
        return None
    return "/".join(parts[:2])


def parse_progress(path: Path) -> dict[str, str]:
    values = {"status": "", "current": "", "next": ""}
    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("**Status:**"):
            values["status"] = stripped.removeprefix("**Status:**").strip()
        elif stripped.startswith("**Current Step:**"):
            values["current"] = stripped.removeprefix("**Current Step:**").strip()
        elif stripped.startswith("**Next Action:**"):
            values["next"] = stripped.removeprefix("**Next Action:**").strip()
    return values


def compact_spec_progress(spec_refs: list[str], limit: int) -> list[str]:
    roots = []
    seen: set[str] = set()
    for ref in spec_refs:
        root = spec_root(ref)
        if root and root not in seen:
            seen.add(root)
            roots.append(root)

    result: list[str] = []
    for root in roots[:limit]:
        progress = parse_progress(Path(root) / "progress.md")
        label = root
        if progress["status"]:
            label += f" [{progress['status']}]"
        if progress["next"]:
            label += f" next={truncate(progress['next'], 120)}"
        result.append(label)
    return result


def latest_text(summary: dict[str, Any], text_limit: int) -> tuple[str, str]:
    if summary.get("task_complete"):
        line, text = summary["task_complete"][-1]
        return f"task_complete line {line}", truncate(text, text_limit)
    if summary.get("assistant_messages"):
        line, phase, text = summary["assistant_messages"][-1]
        label = f"assistant line {line}"
        if phase:
            label += f" phase={phase}"
        return label, truncate(text, text_limit)
    if summary.get("user_messages"):
        line, text = summary["user_messages"][-1]
        return f"user line {line}", truncate(text, text_limit)
    return "none", ""


def hint_for(thread: ThreadInfo, summary: dict[str, Any] | None, goal: dict[str, Any] | None, active_seconds: int) -> str:
    hints: list[str] = []
    if goal:
        hints.append(f"goal:{goal.get('status')}")
    if summary and summary.get("task_complete"):
        hints.append("task-complete")

    latest = ""
    if summary:
        _, latest = latest_text(summary, 500)
    lowered = latest.lower()
    if any(marker in lowered for marker in ("stop after", "stopped", "wait for", "await explicit", "explicit go")):
        hints.append("waiting")
    if any(marker in lowered for marker in ("blocked", "handoff-back", "cannot")):
        hints.append("blocked?")
    if any(marker in lowered for marker in ("done", "complete", "created the child spec", "files written")):
        hints.append("reported")
    if thread.updated_at and time.time() - thread.updated_at <= active_seconds:
        hints.append("recent")
    if not hints:
        hints.append("quiet")
    return ",".join(dict.fromkeys(hints))


def filter_threads(
    threads: list[ThreadInfo],
    cwd: str | None,
    title: str | None,
    session_id: str | None,
    include_archived: bool,
) -> list[ThreadInfo]:
    filtered: list[ThreadInfo] = []
    title_lower = title.lower() if title else None
    for thread in threads:
        if not include_archived and thread.archived:
            continue
        if cwd and thread.cwd and normalise_cwd(thread.cwd) != normalise_cwd(cwd):
            continue
        if title_lower and title_lower not in thread.title.lower():
            continue
        if session_id and session_id not in thread.id:
            continue
        filtered.append(thread)
    return sorted(filtered, key=lambda item: item.updated_at, reverse=True)


def print_table(rows: list[dict[str, Any]]) -> None:
    print("| Updated UTC | Age | Thread | Session | Hint | Specs |")
    print("|---|---:|---|---|---|---|")
    for row in rows:
        specs = "<br>".join(row["spec_progress"]) if row["spec_progress"] else ""
        print(
            "| "
            + " | ".join(
                [
                    row["updated"],
                    row["age"],
                    row["title"].replace("|", "\\|"),
                    row["id"],
                    row["hint"].replace("|", "\\|"),
                    specs.replace("|", "\\|"),
                ]
            )
            + " |"
        )


def transcript_contains(path: Path | None, query: str) -> bool:
    if not path:
        return False
    needle = query.casefold()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return any(needle in line.casefold() for line in handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default="", help="Filter by cwd. Omit to search every project.")
    parser.add_argument("--recent", type=int, default=10, help="Number of recent matching threads to show.")
    parser.add_argument("--title", help="Case-insensitive title filter.")
    parser.add_argument("--session-id", help="Session id or id prefix/sub-string filter.")
    parser.add_argument("--query", help="Case-insensitive exact phrase to find in transcripts.")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--active-minutes", type=int, default=10)
    parser.add_argument("--message-limit", type=int, default=4)
    parser.add_argument("--command-limit", type=int, default=8)
    parser.add_argument("--text-limit", type=int, default=500)
    parser.add_argument("--spec-limit", type=int, default=4)
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    threads = read_state_threads()
    source = "state_5.sqlite"
    if not threads:
        threads = read_index_threads()
        source = "session_index.jsonl"

    cwd_filter = args.cwd or None
    threads = filter_threads(
        threads,
        cwd=cwd_filter,
        title=args.title,
        session_id=args.session_id,
        include_archived=args.include_archived,
    )
    if args.query:
        threads = [thread for thread in threads if transcript_contains(newest_transcript(thread), args.query)]
    threads = threads[: max(1, args.recent)]

    goals = read_goals()
    rows: list[dict[str, Any]] = []
    for thread in threads:
        transcript = newest_transcript(thread)
        summary: dict[str, Any] | None = None
        if transcript:
            summary = summarize_transcript(
                transcript,
                message_limit=max(1, args.message_limit),
                command_limit=max(1, args.command_limit),
                text_limit=max(120, args.text_limit),
            )
        goal = goals.get(thread.id)
        spec_refs = summary.get("referenced_specs", []) if summary else []
        latest_label, latest_excerpt = latest_text(summary, args.text_limit) if summary else ("none", "")
        rows.append(
            {
                "id": thread.id,
                "title": truncate(thread.title, 120),
                "updated": utc(thread.updated_at),
                "updated_at": thread.updated_at,
                "age": age_label(thread.updated_at),
                "cwd": thread.cwd,
                "model": thread.model,
                "reasoning_effort": thread.reasoning_effort,
                "transcript": str(transcript) if transcript else "",
                "hint": hint_for(thread, summary, goal, args.active_minutes * 60),
                "goal": goal,
                "spec_refs": spec_refs,
                "spec_progress": compact_spec_progress(spec_refs, args.spec_limit),
                "latest_label": latest_label,
                "latest_excerpt": latest_excerpt,
                "recent_commands": [
                    {"line": line, "tool": name, "command": truncate(cmd, args.text_limit)}
                    for line, name, cmd in (summary.get("commands", [])[-args.command_limit:] if summary else [])
                ],
            }
        )

    if args.json:
        print(json.dumps({"source": source, "threads": rows}, indent=2))
        return 0

    print("# Codex Active Session Monitor")
    print(f"- Source: {source}")
    print(f"- CWD filter: {cwd_filter or '(none)'}")
    if args.title:
        print(f"- Title filter: {args.title}")
    if args.session_id:
        print(f"- Session filter: {args.session_id}")
    if args.query:
        print(f"- Phrase filter: {args.query}")
    print(f"- Threads shown: {len(rows)}")
    print()
    print_table(rows)

    if args.details:
        for row in rows:
            print()
            print(f"## {row['title']} ({row['id']})")
            print(f"- Updated: {row['updated']} ({row['age']} ago)")
            if row["model"] or row["reasoning_effort"]:
                print(f"- Model: {row['model'] or '?'} / effort={row['reasoning_effort'] or '?'}")
            if row["transcript"]:
                print(f"- Transcript: {row['transcript']}")
            if row["goal"]:
                print(
                    "- Goal: "
                    f"{row['goal'].get('status')} - {truncate(str(row['goal'].get('objective') or ''), args.text_limit)}"
                )
            if row["spec_progress"]:
                print("- Spec status:")
                for item in row["spec_progress"]:
                    print(f"  - {item}")
            print(f"- Latest {row['latest_label']}: {row['latest_excerpt'] or '(none)'}")
            if row["recent_commands"]:
                print("- Recent commands/tools:")
                for command in row["recent_commands"][-5:]:
                    print(f"  - line {command['line']} {command['tool']}: {command['command']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
