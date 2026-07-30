#!/usr/bin/env python3
"""Inspect local Claude Code session transcripts without modifying them."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)(x-fast-service-key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd)\b([\"']?\s*[:=]\s*[\"']?)([^\"'\s,}]+)"),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])sm_[A-Za-z0-9_-]{20,}"),
]

SPEC_PATTERN = re.compile(r"\b(?:spec|spec-archive)/[A-Za-z0-9._/\[\]$-]+")
PATH_PATTERN = re.compile(
    r"\b(?:src|tests|scripts|spec|spec-archive|docs|\.claude)(?:/|\\\\)"
    r"[A-Za-z0-9._/\\\\\[\]$:@+-]+"
)


@dataclass
class LiveRecord:
    session_id: str
    path: Path
    pid: int | None = None
    cwd: str = ""
    entrypoint: str = ""
    kind: str = ""
    name: str = ""
    status: str = ""
    waiting_for: str = ""
    version: str = ""
    updated_at_ms: int = 0
    started_at_ms: int = 0
    process_exists: bool = False


@dataclass
class TranscriptSummary:
    session_id: str
    path: Path
    project_dir: Path
    line_count: int = 0
    latest_ts: str = ""
    latest_epoch: float = 0
    file_mtime: float = 0
    cwd: str = ""
    entrypoint: str = ""
    git_branch: str = ""
    model: str = ""
    title: str = ""
    permission_mode: str = ""
    latest_type: str = ""
    latest_role: str = ""
    latest_user: str = ""
    latest_assistant: str = ""
    first_user: str = ""
    recent_users: list[tuple[int, str, str]] = field(default_factory=list)
    recent_assistants: list[tuple[int, str, str]] = field(default_factory=list)
    recent_tools: list[tuple[int, str, str]] = field(default_factory=list)
    referenced_specs: set[str] = field(default_factory=set)
    referenced_paths: set[str] = field(default_factory=set)
    subagent_count: int = 0
    latest_subagent_mtime: float = 0


def claude_home(args: argparse.Namespace) -> Path:
    return Path(args.claude_home).expanduser()


def redact(text: str) -> str:
    value = text
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)(authorization") or pattern.pattern.startswith("(?i)(bearer"):
            value = pattern.sub(r"\1[REDACTED]", value)
        elif "sk-" in pattern.pattern or "sm_" in pattern.pattern:
            value = pattern.sub("[REDACTED]", value)
        elif "x-fast-service-key" in pattern.pattern:
            value = pattern.sub(r"\1[REDACTED]", value)
        else:
            value = pattern.sub(r"\1\2[REDACTED]", value)
    return value


def truncate(text: str, limit: int = 260) -> str:
    value = redact((text or "").replace("\r\n", "\n").replace("\n", " ").strip())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 17)].rstrip() + " ... [truncated]"


def parse_ts(value: Any) -> float:
    if isinstance(value, (int, float)):
        # Claude JSON files use milliseconds in some places.
        return float(value) / 1000 if value > 10_000_000_000 else float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0
    return 0


def fmt_ts(epoch: float) -> str:
    if not epoch:
        return "?"
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def age_label(epoch: float) -> str:
    if not epoch:
        return "?"
    seconds = max(0, int(datetime.now(timezone.utc).timestamp() - epoch))
    if seconds < 90:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 90:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h"
    return f"{hours // 24}d"


def process_exists(pid: int | None) -> bool:
    """Return whether a process is reachable using a cross-platform probe."""
    if not pid:
        return False
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except (AttributeError, OSError, SystemError):
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def normalise_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def read_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_number, json.loads(line)
            except json.JSONDecodeError:
                yield line_number, {"type": "parse_error", "raw": line}


def message_text(message: Any) -> str:
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            kind = item.get("type")
            if kind in {"text", "thinking"} and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif kind == "tool_use":
                name = item.get("name") or "tool_use"
                tool_input = item.get("input")
                if isinstance(tool_input, dict):
                    brief = tool_input.get("command") or tool_input.get("file_path") or tool_input.get("path") or ""
                else:
                    brief = ""
                parts.append(f"<tool_use {name}: {brief}>")
        return "\n".join(parts)
    return ""


def is_tool_result_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    return isinstance(content, list) and bool(content) and all(
        isinstance(item, dict) and item.get("type") == "tool_result"
        for item in content
    )


def event_text(event: dict[str, Any]) -> str:
    text = message_text(event.get("message"))
    if text:
        return text
    if isinstance(event.get("content"), str):
        return str(event["content"])
    if isinstance(event.get("operation"), str):
        return str(event["operation"])
    return ""


def remember_refs(summary: TranscriptSummary, text: str) -> None:
    if not text:
        return
    summary.referenced_specs.update(SPEC_PATTERN.findall(text))
    summary.referenced_paths.update(PATH_PATTERN.findall(text))


def tool_brief(event: dict[str, Any]) -> tuple[str, str] | None:
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "tool_use":
            continue
        name = str(item.get("name") or "tool_use")
        tool_input = item.get("input")
        if isinstance(tool_input, dict):
            brief = (
                tool_input.get("command")
                or tool_input.get("file_path")
                or tool_input.get("path")
                or tool_input.get("pattern")
                or json.dumps(tool_input, sort_keys=True)[:400]
            )
        else:
            brief = ""
        return name, str(brief)
    return None


def summarize_transcript(path: Path, text_limit: int = 260) -> TranscriptSummary:
    project_dir = path.parent
    summary = TranscriptSummary(
        session_id=path.stem,
        path=path,
        project_dir=project_dir,
        file_mtime=path.stat().st_mtime,
        latest_epoch=path.stat().st_mtime,
    )
    session_artifact_dir = path.with_suffix("")
    subagents = list((session_artifact_dir / "subagents").glob("*.jsonl")) if session_artifact_dir.exists() else []
    summary.subagent_count = len(subagents)
    summary.latest_subagent_mtime = max((p.stat().st_mtime for p in subagents), default=0)

    for line, event in read_jsonl(path):
        summary.line_count = line
        etype = str(event.get("type") or "")
        ts_epoch = parse_ts(event.get("timestamp"))
        if ts_epoch:
            summary.latest_epoch = max(summary.latest_epoch, ts_epoch)
            summary.latest_ts = str(event.get("timestamp"))

        summary.latest_type = etype or summary.latest_type
        if event.get("cwd"):
            summary.cwd = str(event.get("cwd"))
        if event.get("entrypoint"):
            summary.entrypoint = str(event.get("entrypoint"))
        if event.get("gitBranch"):
            summary.git_branch = str(event.get("gitBranch"))

        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        if message:
            if message.get("model"):
                summary.model = str(message.get("model"))
            role = str(message.get("role") or "")
            if role:
                summary.latest_role = role
            text = message_text(message)
            remember_refs(summary, text)
            if role == "user" and text and not is_tool_result_message(message):
                if not summary.first_user:
                    summary.first_user = truncate(text, text_limit)
                summary.latest_user = truncate(text, text_limit)
                summary.recent_users.append((line, str(event.get("timestamp") or ""), truncate(text, text_limit)))
                summary.recent_users = summary.recent_users[-8:]
            elif role == "assistant":
                summary.latest_assistant = truncate(text, text_limit)
                summary.recent_assistants.append((line, str(event.get("timestamp") or ""), truncate(text, text_limit)))
                summary.recent_assistants = summary.recent_assistants[-8:]

        if etype == "last-prompt":
            content = str(event.get("content") or event.get("display") or "")
            summary.latest_user = truncate(content, text_limit)
            if not summary.first_user:
                summary.first_user = truncate(content, text_limit)
            remember_refs(summary, content)
        elif etype == "ai-title":
            summary.title = str(event.get("content") or event.get("title") or "")
        elif etype == "permission-mode":
            summary.permission_mode = str(event.get("mode") or event.get("permissionMode") or event.get("permission-mode") or "")

        brief = tool_brief(event)
        if brief:
            name, value = brief
            summary.recent_tools.append((line, name, truncate(value, text_limit)))
            summary.recent_tools = summary.recent_tools[-20:]
            remember_refs(summary, value)

        text = event_text(event)
        remember_refs(summary, text)

    if not summary.latest_ts:
        summary.latest_ts = fmt_ts(summary.latest_epoch)
    return summary


def find_project_dirs(home: Path) -> list[Path]:
    projects = home / "projects"
    if not projects.exists():
        return []
    return sorted([p for p in projects.iterdir() if p.is_dir()])


def find_transcripts(home: Path, session_id: str | None = None) -> list[Path]:
    dirs = find_project_dirs(home)
    paths: list[Path] = []
    if session_id:
        for project in dirs:
            paths.extend(project.glob(f"{session_id}.jsonl"))
    else:
        for project in dirs:
            paths.extend(project.glob("*.jsonl"))
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)


def read_live_records(home: Path) -> dict[str, LiveRecord]:
    records: dict[str, LiveRecord] = {}
    sessions_dir = home / "sessions"
    if not sessions_dir.exists():
        return records
    for path in sessions_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        session_id = data.get("sessionId")
        if not isinstance(session_id, str):
            continue
        pid = data.get("pid")
        try:
            pid_int = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            pid_int = None
        record = LiveRecord(
            session_id=session_id,
            path=path,
            pid=pid_int,
            cwd=str(data.get("cwd") or ""),
            entrypoint=str(data.get("entrypoint") or ""),
            kind=str(data.get("kind") or ""),
            name=str(data.get("name") or ""),
            status=str(data.get("status") or ""),
            waiting_for=str(data.get("waitingFor") or ""),
            version=str(data.get("version") or ""),
            updated_at_ms=int(data.get("updatedAt") or data.get("startedAt") or 0),
            started_at_ms=int(data.get("startedAt") or 0),
            process_exists=process_exists(pid_int),
        )
        records[session_id] = record
    return records


def read_history(home: Path) -> dict[str, list[dict[str, Any]]]:
    path = home / "history.jsonl"
    history: dict[str, list[dict[str, Any]]] = {}
    if not path.exists():
        return history
    for _, event in read_jsonl(path):
        session_id = event.get("sessionId")
        if not isinstance(session_id, str):
            continue
        history.setdefault(session_id, []).append(event)
        history[session_id] = history[session_id][-12:]
    return history


def session_label(summary: TranscriptSummary, live: LiveRecord | None) -> str:
    parts = []
    if summary.entrypoint or (live and live.entrypoint):
        parts.append(summary.entrypoint or live.entrypoint)
    if summary.cwd or (live and live.cwd):
        parts.append(summary.cwd or live.cwd)
    if live:
        if live.status:
            parts.append(f"status={live.status}")
        if live.waiting_for:
            parts.append(f"waiting={live.waiting_for}")
        if live.process_exists:
            parts.append("pid-live")
    if summary.subagent_count:
        parts.append(f"subagents={summary.subagent_count}")
    return "; ".join(parts)


def print_heading(title: str) -> None:
    print(f"\n## {title}")


def transcript_contains(path: Path, query: str) -> bool:
    needle = query.casefold()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return any(needle in line.casefold() for line in handle)


def monitor(args: argparse.Namespace) -> int:
    home = claude_home(args)
    live_records = read_live_records(home)
    history = read_history(home)
    cwd_filter = normalise_path(args.cwd) if args.cwd else ""

    summaries: list[TranscriptSummary] = []
    for path in find_transcripts(home):
        summary = summarize_transcript(path, args.text_limit)
        effective_cwd = summary.cwd or (live_records.get(summary.session_id).cwd if summary.session_id in live_records else "")
        if cwd_filter and normalise_path(effective_cwd or os.curdir) != cwd_filter:
            continue
        if args.entrypoint and (summary.entrypoint or live_records.get(summary.session_id, LiveRecord("", Path(""))).entrypoint) != args.entrypoint:
            continue
        if args.title and args.title.casefold() not in summary.title.casefold():
            continue
        if args.query and not transcript_contains(path, args.query):
            continue
        summaries.append(summary)

    summaries.sort(key=lambda s: max(s.latest_epoch, s.file_mtime, s.latest_subagent_mtime), reverse=True)
    summaries = summaries[: max(1, args.recent)]

    print("# Claude Session Monitor")
    print(f"- Claude home: {home}")
    if cwd_filter:
        print(f"- CWD filter: {cwd_filter}")
    if args.title:
        print(f"- Title filter: {args.title}")
    if args.query:
        print(f"- Phrase filter: {args.query}")
    print(f"- Sessions shown: {len(summaries)}")
    print()
    print("| Updated UTC | Age | Entrypoint | Session | CWD / Status | Last user prompt |")
    print("|---|---:|---|---|---|---|")
    for summary in summaries:
        live = live_records.get(summary.session_id)
        updated = max(summary.latest_epoch, summary.file_mtime, summary.latest_subagent_mtime)
        effective_entry = summary.entrypoint or (live.entrypoint if live else "")
        effective_cwd = summary.cwd or (live.cwd if live else "")
        status_bits = []
        if live and live.status:
            status_bits.append(live.status)
        if live and live.waiting_for:
            status_bits.append(f"waiting:{live.waiting_for}")
        if live and live.process_exists:
            status_bits.append("pid-live")
        if summary.subagent_count:
            status_bits.append(f"{summary.subagent_count} subagents")
        cwd_status = truncate(" ".join([effective_cwd, *status_bits]), 180)
        last_prompt = summary.latest_user
        if not last_prompt and history.get(summary.session_id):
            last_prompt = truncate(str(history[summary.session_id][-1].get("display") or ""), args.text_limit)
        print(
            f"| {fmt_ts(updated)} | {age_label(updated)} | {effective_entry or '?'} | "
            f"`{summary.session_id}` | {cwd_status or '?'} | {last_prompt or '?'} |"
        )

    if not args.details:
        return 0

    for summary in summaries:
        live = live_records.get(summary.session_id)
        print_heading(f"{summary.session_id}")
        print(f"- Transcript: {summary.path}")
        print(f"- Lines: {summary.line_count}")
        print(f"- Label: {session_label(summary, live)}")
        if live:
            live_epoch = parse_ts(live.updated_at_ms)
            print(
                f"- Live record: {live.path} pid={live.pid} processExists={live.process_exists} "
                f"updated={fmt_ts(live_epoch)} version={live.version}"
            )
        if summary.title:
            print(f"- Title: {truncate(summary.title, args.text_limit)}")
        if summary.first_user:
            print(f"- First user: {summary.first_user}")
        if summary.latest_user:
            print(f"- Latest user: {summary.latest_user}")
        if summary.latest_assistant:
            print(f"- Latest assistant: {summary.latest_assistant}")
        if history.get(summary.session_id):
            print("- Recent history prompts:")
            for event in history[summary.session_id][-5:]:
                print(f"  - {fmt_ts(parse_ts(event.get('timestamp')))} {truncate(str(event.get('display') or ''), args.text_limit)}")
        if summary.referenced_specs:
            print("- Referenced specs: " + ", ".join(sorted(summary.referenced_specs)[:12]))
        if summary.recent_tools:
            print("- Recent tools:")
            for line, name, value in summary.recent_tools[-8:]:
                print(f"  - line {line} {name}: {value}")

    return 0


def inspect(args: argparse.Namespace) -> int:
    home = claude_home(args)
    session_id = args.session_id.strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{8,}(?:-[0-9a-fA-F-]{4,})*", session_id):
        raise SystemExit(f"Invalid-looking Claude session id: {session_id}")

    transcripts = find_transcripts(home, session_id)
    live = read_live_records(home).get(session_id)
    history = read_history(home).get(session_id, [])

    print(f"# Claude Session Summary: {session_id}")
    print(f"- Claude home: {home}")

    print_heading("Live Session Record")
    if live:
        print(f"- File: {live.path}")
        print(f"- PID: {live.pid} processExists={live.process_exists}")
        print(f"- CWD: {live.cwd}")
        print(f"- Entrypoint: {live.entrypoint}")
        print(f"- Status: {live.status or '(none)'}")
        if live.waiting_for:
            print(f"- Waiting for: {live.waiting_for}")
        print(f"- Version: {live.version}")
        print(f"- Updated: {fmt_ts(parse_ts(live.updated_at_ms))}")
    else:
        print(f"- No matching `{home / 'sessions'}` record.")

    print_heading("Transcript Files")
    if not transcripts:
        print("- None found.")
    else:
        for path in transcripts:
            print(f"- {path}")

    print_heading("History Prompts")
    if history:
        for event in history[-10:]:
            print(f"- {fmt_ts(parse_ts(event.get('timestamp')))} {truncate(str(event.get('display') or ''), args.text_limit)}")
    else:
        print("- None found.")

    if not transcripts:
        return 1

    for path in transcripts:
        summary = summarize_transcript(path, args.text_limit)
        print_heading(f"Transcript: {path}")
        print(f"- Lines: {summary.line_count}")
        print(f"- Latest: {fmt_ts(max(summary.latest_epoch, summary.file_mtime))}")
        print(f"- Entrypoint: {summary.entrypoint or (live.entrypoint if live else '?')}")
        print(f"- CWD: {summary.cwd or (live.cwd if live else '?')}")
        print(f"- Git branch: {summary.git_branch or '?'}")
        print(f"- Model: {summary.model or '?'}")
        print(f"- Subagents: {summary.subagent_count}")

        print_heading("Recent User Messages")
        for line, ts, text in summary.recent_users[-max(1, args.message_limit):]:
            print(f"- line {line} {ts or ''}: {text}")
        if not summary.recent_users:
            print("- None found.")

        print_heading("Recent Assistant Messages")
        for line, ts, text in summary.recent_assistants[-max(1, args.message_limit):]:
            print(f"- line {line} {ts or ''}: {text}")
        if not summary.recent_assistants:
            print("- None found.")

        print_heading("Recent Tools")
        for line, name, value in summary.recent_tools[-max(1, args.tool_limit):]:
            print(f"- line {line} {name}: {value}")
        if not summary.recent_tools:
            print("- None found.")

        print_heading("Referenced Specs")
        if summary.referenced_specs:
            for ref in sorted(summary.referenced_specs)[:80]:
                print(f"- {ref}")
        else:
            print("- None found.")

        print_heading("Referenced Paths")
        if summary.referenced_paths:
            for ref in sorted(summary.referenced_paths)[:80]:
                print(f"- {ref}")
        else:
            print("- None found.")

        session_artifact_dir = path.with_suffix("")
        subagent_dir = session_artifact_dir / "subagents"
        if subagent_dir.exists():
            print_heading("Subagent Files")
            for subagent in sorted(subagent_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:40]:
                print(f"- {fmt_ts(subagent.stat().st_mtime)} {subagent.stat().st_size} bytes {subagent}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude-home", default=str(Path.home() / ".claude"), help="Path to the Claude Code .claude directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    monitor_parser = sub.add_parser("monitor", help="List recent Claude sessions across project stores")
    monitor_parser.add_argument("--recent", type=int, default=8)
    monitor_parser.add_argument("--cwd", help="Filter by exact working directory")
    monitor_parser.add_argument("--entrypoint", help="Filter by exact entrypoint value.")
    monitor_parser.add_argument("--title", help="Case-insensitive conversation-title filter.")
    monitor_parser.add_argument("--query", help="Case-insensitive exact phrase to find in transcripts.")
    monitor_parser.add_argument("--details", action="store_true")
    monitor_parser.add_argument("--text-limit", type=int, default=260)
    monitor_parser.set_defaults(func=monitor)

    inspect_parser = sub.add_parser("inspect", help="Summarize one Claude session by id")
    inspect_parser.add_argument("session_id")
    inspect_parser.add_argument("--message-limit", type=int, default=8)
    inspect_parser.add_argument("--tool-limit", type=int, default=20)
    inspect_parser.add_argument("--text-limit", type=int, default=420)
    inspect_parser.set_defaults(func=inspect)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
