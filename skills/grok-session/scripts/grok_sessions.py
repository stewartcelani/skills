#!/usr/bin/env python3
"""Inspect local Grok CLI session transcripts without modifying them."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote


SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)(x-fast-service-key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)"),
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd)\b([\"']?\s*[:=]\s*[\"']?)([^\"'\s,}]+)"
    ),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])sm_[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])xai-[A-Za-z0-9_-]{20,}"),
]

SPEC_PATTERN = re.compile(r"\b(?:spec|spec-archive)/[A-Za-z0-9._/\[\]$-]+")
PATH_PATTERN = re.compile(
    r"\b(?:src|tests|scripts|spec|spec-archive|docs|\.grok|\.claude|\.codex|\.agents)"
    r"(?:/|\\\\)[A-Za-z0-9._/\\\\\[\]$:@+-]+"
)

SESSION_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

try:
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, OSError):
    pass


@dataclass
class LiveRecord:
    session_id: str
    pid: int | None = None
    cwd: str = ""
    opened_at: str = ""
    process_exists: bool = False


@dataclass
class SessionMeta:
    session_id: str
    path: Path
    cwd: str = ""
    title: str = ""
    session_summary: str = ""
    created_at: str = ""
    updated_at: str = ""
    updated_epoch: float = 0
    num_messages: int = 0
    num_chat_messages: int = 0
    model: str = ""
    agent_name: str = ""
    git_branch: str = ""
    git_root: str = ""
    head_commit: str = ""
    parent_session_id: str = ""
    reasoning_effort: str = ""
    sandbox_profile: str = ""
    file_mtime: float = 0


@dataclass
class TranscriptSummary:
    session_id: str
    path: Path
    line_count: int = 0
    latest_epoch: float = 0
    first_user: str = ""
    latest_user: str = ""
    latest_assistant: str = ""
    recent_users: list[tuple[int, str, str]] = field(default_factory=list)
    recent_assistants: list[tuple[int, str, str]] = field(default_factory=list)
    recent_tools: list[tuple[int, str, str]] = field(default_factory=list)
    referenced_specs: set[str] = field(default_factory=set)
    referenced_paths: set[str] = field(default_factory=set)
    tool_names: set[str] = field(default_factory=set)


def default_grok_home() -> Path:
    env = os.environ.get("GROK_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".grok"


def grok_home(args: argparse.Namespace) -> Path:
    return Path(args.grok_home).expanduser()


def redact(text: str) -> str:
    value = text
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)(authorization") or pattern.pattern.startswith("(?i)(bearer"):
            value = pattern.sub(r"\1[REDACTED]", value)
        elif any(token in pattern.pattern for token in ("sk-", "sm_", "xai-")):
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
        number = float(value)
        # Grok update timestamps are often unix seconds; ms if huge.
        if number > 10_000_000_000:
            return number / 1000
        return number
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
    if not pid:
        return False
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                process_query_limited_information, False, pid
            )
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
    value = path[4:] if path.startswith("\\\\?\\") else path
    return os.path.normcase(os.path.abspath(os.path.expanduser(value)))


def decode_cwd_dirname(name: str, group_dir: Path | None = None) -> str:
    if group_dir is not None:
        marker = group_dir / ".cwd"
        if marker.exists():
            try:
                value = marker.read_text(encoding="utf-8", errors="replace").strip()
                if value:
                    return value
            except OSError:
                pass
    return unquote(name)


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


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


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if content.get("type") == "text" and isinstance(content.get("text"), str):
            return content["text"]
        nested = content.get("content")
        if nested is not None and nested is not content:
            return content_text(nested)
        return ""
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = content_text(item)
            if text:
                parts.append(text)
        return "\n".join(parts)
    return ""


def remember_refs(summary: TranscriptSummary, text: str) -> None:
    if not text:
        return
    summary.referenced_specs.update(SPEC_PATTERN.findall(text))
    summary.referenced_paths.update(PATH_PATTERN.findall(text))


def tool_brief(update: dict[str, Any]) -> tuple[str, str] | None:
    name = (
        str(update.get("title") or "")
        or str(((update.get("_meta") or {}).get("x.ai/tool") or {}).get("name") or "")
        or str(update.get("toolCallId") or "tool")
    )
    raw_input = update.get("rawInput")
    brief = ""
    if isinstance(raw_input, dict):
        brief = str(
            raw_input.get("command")
            or raw_input.get("file_path")
            or raw_input.get("path")
            or raw_input.get("pattern")
            or raw_input.get("query")
            or raw_input.get("description")
            or json.dumps(raw_input, sort_keys=True)[:400]
        )
    elif isinstance(raw_input, str):
        brief = raw_input
    if not brief and isinstance(update.get("content"), list):
        brief = truncate(content_text(update.get("content")), 200)
    return name, brief


def flush_chunk(
    summary: TranscriptSummary,
    role: str,
    text: str,
    line: int,
    ts: str,
    text_limit: int,
) -> None:
    cleaned = truncate(text, text_limit)
    if not cleaned:
        return
    remember_refs(summary, text)
    if role == "user":
        if not summary.first_user:
            summary.first_user = cleaned
        summary.latest_user = cleaned
        summary.recent_users.append((line, ts, cleaned))
        summary.recent_users = summary.recent_users[-8:]
    elif role == "assistant":
        summary.latest_assistant = cleaned
        summary.recent_assistants.append((line, ts, cleaned))
        summary.recent_assistants = summary.recent_assistants[-8:]


def summarize_updates(path: Path, text_limit: int = 260) -> TranscriptSummary:
    summary = TranscriptSummary(session_id=path.parent.name, path=path)
    pending_role = ""
    pending_text: list[str] = []
    pending_line = 0
    pending_ts = ""

    def flush() -> None:
        nonlocal pending_role, pending_text, pending_line, pending_ts
        if pending_role and pending_text:
            flush_chunk(
                summary,
                pending_role,
                "".join(pending_text),
                pending_line,
                pending_ts,
                text_limit,
            )
        pending_role = ""
        pending_text = []
        pending_line = 0
        pending_ts = ""

    for line, event in read_jsonl(path):
        summary.line_count = line
        ts_epoch = parse_ts(event.get("timestamp"))
        meta = event.get("params") if isinstance(event.get("params"), dict) else {}
        event_meta = meta.get("_meta") if isinstance(meta.get("_meta"), dict) else {}
        if not ts_epoch:
            ts_epoch = parse_ts(event_meta.get("agentTimestampMs"))
        if ts_epoch:
            summary.latest_epoch = max(summary.latest_epoch, ts_epoch)

        update = meta.get("update") if isinstance(meta.get("update"), dict) else {}
        if not update and isinstance(event.get("update"), dict):
            update = event["update"]
        kind = str(update.get("sessionUpdate") or event.get("sessionUpdate") or "")

        if kind in {"user_message_chunk", "agent_message_chunk"}:
            role = "user" if kind.startswith("user_") else "assistant"
            text = content_text(update.get("content"))
            if role != pending_role:
                flush()
                pending_role = role
                pending_line = line
                pending_ts = str(event.get("timestamp") or "")
            pending_text.append(text)
            continue

        # Non-chunk events break the current chunk assembly.
        flush()

        if kind == "tool_call":
            brief = tool_brief(update)
            if brief:
                name, value = brief
                summary.tool_names.add(name)
                summary.recent_tools.append((line, name, truncate(value, text_limit)))
                summary.recent_tools = summary.recent_tools[-20:]
                remember_refs(summary, value)
        elif kind == "tool_call_update":
            raw_input = update.get("rawInput")
            if isinstance(raw_input, dict):
                value = str(
                    raw_input.get("command")
                    or raw_input.get("file_path")
                    or raw_input.get("path")
                    or ""
                )
                name = str(update.get("title") or "tool_call_update")
                if value:
                    summary.tool_names.add(name)
                    remember_refs(summary, value)
        elif kind in {"available_commands_update", "hook_execution", "agent_thought_chunk"}:
            pass
        else:
            text = content_text(update.get("content")) or content_text(update)
            remember_refs(summary, text)

    flush()
    if not summary.latest_epoch and path.exists():
        summary.latest_epoch = path.stat().st_mtime
    return summary


def summarize_chat_history(path: Path, text_limit: int = 260) -> TranscriptSummary:
    """Fallback summarizer when updates.jsonl is missing after a crash."""
    summary = TranscriptSummary(session_id=path.parent.name, path=path)
    for line, event in read_jsonl(path):
        summary.line_count = line
        role = str(event.get("type") or event.get("role") or "")
        if role not in {"user", "assistant"}:
            continue
        text = content_text(event.get("content"))
        if not text.strip():
            continue
        # Skip synthetic/system-reminder user wrappers when a real query is nested later.
        if role == "user" and "<system-reminder>" in text and "<user_query>" not in text:
            continue
        query = text
        if "<user_query>" in text:
            start = text.find("<user_query>") + len("<user_query>")
            end = text.find("</user_query>")
            if end > start:
                query = text[start:end].strip()
        flush_chunk(summary, role, query, line, "", text_limit)
    if not summary.latest_epoch and path.exists():
        summary.latest_epoch = path.stat().st_mtime
    return summary


def summarize_session_transcript(session_dir: Path, text_limit: int = 260) -> TranscriptSummary | None:
    updates = session_dir / "updates.jsonl"
    if updates.exists():
        return summarize_updates(updates, text_limit)
    chat = session_dir / "chat_history.jsonl"
    if chat.exists():
        return summarize_chat_history(chat, text_limit)
    return None


def load_session_meta(summary_path: Path) -> SessionMeta | None:
    data = read_json(summary_path)
    if not isinstance(data, dict):
        return None
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    session_id = str(info.get("id") or summary_path.parent.name)
    cwd = str(info.get("cwd") or "")
    if not cwd:
        cwd = decode_cwd_dirname(summary_path.parent.parent.name, summary_path.parent.parent)
    updated = str(data.get("updated_at") or data.get("last_active_at") or "")
    title = str(data.get("generated_title") or data.get("session_summary") or "")
    return SessionMeta(
        session_id=session_id,
        path=summary_path.parent,
        cwd=cwd,
        title=title,
        session_summary=str(data.get("session_summary") or ""),
        created_at=str(data.get("created_at") or ""),
        updated_at=updated,
        updated_epoch=parse_ts(updated) or summary_path.stat().st_mtime,
        num_messages=int(data.get("num_messages") or 0),
        num_chat_messages=int(data.get("num_chat_messages") or 0),
        model=str(data.get("current_model_id") or ""),
        agent_name=str(data.get("agent_name") or ""),
        git_branch=str(data.get("head_branch") or ""),
        git_root=str(data.get("git_root_dir") or ""),
        head_commit=str(data.get("head_commit") or ""),
        parent_session_id=str(data.get("parent_session_id") or ""),
        reasoning_effort=str(data.get("reasoning_effort") or ""),
        sandbox_profile=str(data.get("sandbox_profile") or ""),
        file_mtime=summary_path.stat().st_mtime,
    )


def find_session_dirs(home: Path) -> list[Path]:
    sessions = home / "sessions"
    if not sessions.exists():
        return []
    dirs: list[Path] = []
    for group in sessions.iterdir():
        if not group.is_dir() or group.name.startswith("."):
            continue
        for child in group.iterdir():
            if not child.is_dir():
                continue
            if (
                (child / "summary.json").exists()
                or (child / "updates.jsonl").exists()
                or (child / "chat_history.jsonl").exists()
            ):
                dirs.append(child)
    return dirs


def find_session_dir(home: Path, session_id: str) -> Path | None:
    sessions = home / "sessions"
    if not sessions.exists():
        return None
    matches = [
        path
        for path in sessions.rglob(session_id)
        if path.is_dir()
        and (
            (path / "summary.json").exists()
            or (path / "updates.jsonl").exists()
            or (path / "chat_history.jsonl").exists()
        )
    ]
    if not matches:
        return None

    def sort_key(path: Path) -> float:
        for name in ("summary.json", "updates.jsonl", "chat_history.jsonl"):
            candidate = path / name
            if candidate.exists():
                return candidate.stat().st_mtime
        return path.stat().st_mtime

    return max(matches, key=sort_key)


def session_meta_from_dir(session_dir: Path) -> SessionMeta:
    summary_path = session_dir / "summary.json"
    meta = load_session_meta(summary_path) if summary_path.exists() else None
    if meta:
        return meta
    group = session_dir.parent
    cwd = decode_cwd_dirname(group.name, group)
    mtime = 0.0
    for name in ("updates.jsonl", "chat_history.jsonl", "summary.json"):
        path = session_dir / name
        if path.exists():
            mtime = max(mtime, path.stat().st_mtime)
    return SessionMeta(
        session_id=session_dir.name,
        path=session_dir,
        cwd=cwd,
        updated_epoch=mtime,
        file_mtime=mtime,
    )


def read_live_records(home: Path) -> dict[str, LiveRecord]:
    records: dict[str, LiveRecord] = {}
    path = home / "active_sessions.json"
    data = read_json(path)
    if not isinstance(data, list):
        return records
    for item in data:
        if not isinstance(item, dict):
            continue
        session_id = item.get("session_id")
        if not isinstance(session_id, str):
            continue
        pid = item.get("pid")
        try:
            pid_int = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            pid_int = None
        records[session_id] = LiveRecord(
            session_id=session_id,
            pid=pid_int,
            cwd=str(item.get("cwd") or ""),
            opened_at=str(item.get("opened_at") or ""),
            process_exists=process_exists(pid_int),
        )
    return records


def search_index_ids(home: Path, query: str, limit: int = 50) -> set[str]:
    db_path = home / "sessions" / "session_search.sqlite"
    if not db_path.exists():
        return set()
    needle = query.strip()
    if not needle:
        return set()
    uri = db_path.resolve().as_posix()
    try:
        connection = sqlite3.connect(f"file:{uri}?mode=ro", uri=True)
    except sqlite3.Error:
        return set()
    try:
        rows = connection.execute(
            """
            select session_id from session_docs
            where title like ? or content like ?
            order by updated_at desc
            limit ?
            """,
            (f"%{needle}%", f"%{needle}%", max(1, limit)),
        ).fetchall()
        return {str(row[0]) for row in rows}
    except sqlite3.Error:
        return set()
    finally:
        connection.close()


def transcript_contains(path: Path, query: str) -> bool:
    needle = query.casefold()
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return any(needle in line.casefold() for line in handle)
    except OSError:
        return False


def read_signals(session_dir: Path) -> dict[str, Any]:
    data = read_json(session_dir / "signals.json")
    return data if isinstance(data, dict) else {}


def read_plan(session_dir: Path) -> dict[str, Any]:
    data = read_json(session_dir / "plan.json")
    return data if isinstance(data, dict) else {}


def print_heading(title: str) -> None:
    print(f"\n## {title}")


def monitor(args: argparse.Namespace) -> int:
    home = grok_home(args)
    live_records = read_live_records(home)
    cwd_filter = normalise_path(args.cwd) if args.cwd else ""
    query_ids = search_index_ids(home, args.query, limit=max(50, args.recent * 5)) if args.query else set()

    metas: list[SessionMeta] = []
    for session_dir in find_session_dirs(home):
        meta = session_meta_from_dir(session_dir)
        effective_cwd = meta.cwd or (live_records.get(meta.session_id).cwd if meta.session_id in live_records else "")
        if cwd_filter:
            if not effective_cwd or normalise_path(effective_cwd) != cwd_filter:
                continue
        if args.title:
            hay = f"{meta.title} {meta.session_summary}".casefold()
            if args.title.casefold() not in hay:
                continue
        if args.query:
            updates = session_dir / "updates.jsonl"
            chat = session_dir / "chat_history.jsonl"
            in_index = meta.session_id in query_ids
            in_title = args.query.casefold() in f"{meta.title} {meta.session_summary}".casefold()
            in_updates = updates.exists() and transcript_contains(updates, args.query)
            in_chat = chat.exists() and transcript_contains(chat, args.query)
            if not (in_index or in_title or in_updates or in_chat):
                continue
        metas.append(meta)

    metas.sort(key=lambda item: max(item.updated_epoch, item.file_mtime), reverse=True)
    metas = metas[: max(1, args.recent)]

    print("# Grok Session Monitor")
    print(f"- Grok home: {home}")
    if cwd_filter:
        print(f"- CWD filter: {cwd_filter}")
    if args.title:
        print(f"- Title filter: {args.title}")
    if args.query:
        print(f"- Phrase filter: {args.query}")
    print(f"- Sessions shown: {len(metas)}")
    print()
    print("| Updated UTC | Age | Model | Session | CWD / Status | Title / last user |")
    print("|---|---:|---|---|---|---|")

    detail_rows: list[tuple[SessionMeta, TranscriptSummary | None, LiveRecord | None, dict[str, Any]]] = []
    for meta in metas:
        live = live_records.get(meta.session_id)
        transcript: TranscriptSummary | None = None
        if args.details or not meta.title:
            transcript = summarize_session_transcript(meta.path, args.text_limit)

        status_bits: list[str] = []
        if live and live.process_exists:
            status_bits.append("pid-live")
        elif live:
            status_bits.append("stale-active")
        signals = read_signals(meta.path) if args.details else {}
        if signals.get("compactionCount"):
            status_bits.append(f"compactions={signals.get('compactionCount')}")
        cwd_status = truncate(" ".join([meta.cwd, *status_bits]).strip(), 180)
        preview = meta.title or (transcript.latest_user if transcript else "") or meta.session_summary
        print(
            f"| {fmt_ts(meta.updated_epoch)} | {age_label(meta.updated_epoch)} | "
            f"{meta.model or '?'} | `{meta.session_id}` | {cwd_status or '?'} | "
            f"{truncate(preview, args.text_limit) or '?'} |"
        )
        detail_rows.append((meta, transcript, live, signals))

    if not args.details:
        return 0

    for meta, transcript, live, signals in detail_rows:
        if transcript is None:
            transcript = summarize_session_transcript(meta.path, args.text_limit)
        print_heading(meta.session_id)
        print(f"- Session dir: {meta.path}")
        transcript_path = meta.path / "updates.jsonl"
        if not transcript_path.exists():
            transcript_path = meta.path / "chat_history.jsonl"
        print(f"- Transcript: {transcript_path}")
        print(f"- Title: {truncate(meta.title or meta.session_summary, args.text_limit) or '?'}")
        print(f"- CWD: {meta.cwd or '?'}")
        print(f"- Branch: {meta.git_branch or '?'} commit={meta.head_commit or '?'}")
        print(f"- Model: {meta.model or '?'} effort={meta.reasoning_effort or '?'} agent={meta.agent_name or '?'}")
        print(f"- Messages: updates={meta.num_messages} chat={meta.num_chat_messages}")
        if meta.parent_session_id:
            print(f"- Parent session: {meta.parent_session_id}")
        if live:
            print(
                f"- Live: pid={live.pid} processExists={live.process_exists} "
                f"opened={live.opened_at or '?'}"
            )
        if signals:
            print(
                f"- Context: {signals.get('contextTokensUsed', '?')}/"
                f"{signals.get('contextWindowTokens', '?')} "
                f"({signals.get('contextWindowUsage', '?')}%) "
                f"tools={signals.get('toolCallCount', '?')} "
                f"turns={signals.get('turnCount', '?')}"
            )
            tools_used = signals.get("toolsUsed")
            if isinstance(tools_used, list) and tools_used:
                print(f"- Tools used: {', '.join(str(item) for item in tools_used[:20])}")
        if transcript:
            if transcript.first_user:
                print(f"- First user: {transcript.first_user}")
            if transcript.latest_user:
                print(f"- Latest user: {transcript.latest_user}")
            if transcript.latest_assistant:
                print(f"- Latest assistant: {transcript.latest_assistant}")
            if transcript.referenced_specs:
                print("- Referenced specs: " + ", ".join(sorted(transcript.referenced_specs)[:12]))
            if transcript.recent_tools:
                print("- Recent tools:")
                for line, name, value in transcript.recent_tools[-8:]:
                    print(f"  - line {line} {name}: {value}")
    return 0


def inspect(args: argparse.Namespace) -> int:
    home = grok_home(args)
    session_id = args.session_id.strip()
    if not SESSION_ID_RE.fullmatch(session_id):
        raise SystemExit(f"Invalid-looking Grok session id: {session_id}")

    session_dir = find_session_dir(home, session_id)
    live = read_live_records(home).get(session_id)
    meta = session_meta_from_dir(session_dir) if session_dir else None

    print(f"# Grok Session Summary: {session_id}")
    print(f"- Grok home: {home}")

    print_heading("Session Directory")
    if session_dir:
        print(f"- {session_dir}")
    else:
        print("- None found.")
        return 1

    print_heading("Metadata")
    if meta and (session_dir / "summary.json").exists():
        print(f"- Title: {meta.title or meta.session_summary or '?'}")
        print(f"- Created: {meta.created_at or '?'}")
        print(f"- Updated: {meta.updated_at or fmt_ts(meta.updated_epoch)}")
        print(f"- CWD: {meta.cwd or '?'}")
        print(f"- Git: branch={meta.git_branch or '?'} root={meta.git_root or '?'} commit={meta.head_commit or '?'}")
        print(f"- Model: {meta.model or '?'} effort={meta.reasoning_effort or '?'}")
        print(f"- Agent: {meta.agent_name or '?'} sandbox={meta.sandbox_profile or '?'}")
        print(f"- Messages: updates={meta.num_messages} chat={meta.num_chat_messages}")
        if meta.parent_session_id:
            print(f"- Parent session: {meta.parent_session_id}")
    elif meta:
        print(f"- summary.json missing; inferred CWD: {meta.cwd or '?'}")
        print(f"- Updated (file mtime): {fmt_ts(meta.updated_epoch)}")
    else:
        print("- summary.json missing or unreadable.")

    print_heading("Live Session Record")
    if live:
        print(f"- PID: {live.pid} processExists={live.process_exists}")
        print(f"- CWD: {live.cwd or '?'}")
        print(f"- Opened: {live.opened_at or '?'}")
    else:
        print("- No matching active_sessions.json entry.")

    signals = read_signals(session_dir)
    print_heading("Signals")
    if signals:
        interesting = [
            "turnCount",
            "userMessageCount",
            "assistantMessageCount",
            "toolCallCount",
            "errorCount",
            "toolFailureCount",
            "compactionCount",
            "contextTokensUsed",
            "contextWindowTokens",
            "contextWindowUsage",
            "primaryModelId",
            "sessionDurationSeconds",
            "agentFilesTouched",
            "gitCommitCount",
            "prCreatedCount",
        ]
        for key in interesting:
            if key in signals and signals[key] not in (None, 0, "", [], {}):
                print(f"- {key}: {signals[key]}")
        tools_used = signals.get("toolsUsed")
        if isinstance(tools_used, list) and tools_used:
            print(f"- toolsUsed: {', '.join(str(item) for item in tools_used[:20])}")
    else:
        print("- None found.")

    plan = read_plan(session_dir)
    print_heading("Plan / Todos")
    todos = plan.get("todos") if isinstance(plan.get("todos"), dict) else plan
    if isinstance(todos, dict) and todos:
        for key, value in list(todos.items())[:40]:
            if isinstance(value, dict):
                status = value.get("status") or value.get("state") or ""
                content = value.get("content") or value.get("text") or value.get("title") or value
                print(f"- {key}: {status} {truncate(str(content), args.text_limit)}")
            else:
                print(f"- {key}: {truncate(str(value), args.text_limit)}")
    else:
        print("- None found.")

    updates = session_dir / "updates.jsonl"
    chat = session_dir / "chat_history.jsonl"
    print_heading("Transcript Files")
    for name in (
        "updates.jsonl",
        "chat_history.jsonl",
        "summary.json",
        "signals.json",
        "plan.json",
        "prompt_context.json",
    ):
        path = session_dir / name
        if path.exists():
            print(f"- {path} ({path.stat().st_size} bytes)")
    terminal_dir = session_dir / "terminal"
    if terminal_dir.exists():
        count = sum(1 for _ in terminal_dir.glob("*"))
        print(f"- terminal/: {count} log file(s) present (not read by default)")
    rewind = session_dir / "rewind_points.jsonl"
    if rewind.exists():
        print(f"- rewind_points.jsonl present (file snapshots not read by default)")

    summary = summarize_session_transcript(session_dir, args.text_limit)
    if not summary:
        print("\n- No updates.jsonl or chat_history.jsonl; cannot summarize conversation.")
        return 1

    source = updates if updates.exists() else chat
    print_heading(f"Transcript: {source}")
    if not updates.exists() and chat.exists():
        print("- Note: summarizing chat_history.jsonl because updates.jsonl is missing.")
    print(f"- Lines: {summary.line_count}")
    print(f"- Latest: {fmt_ts(summary.latest_epoch)}")

    print_heading("Recent User Messages")
    for line, ts, text in summary.recent_users[-max(1, args.message_limit) :]:
        print(f"- line {line} {ts or ''}: {text}")
    if not summary.recent_users:
        print("- None found.")

    print_heading("Recent Assistant Messages")
    for line, ts, text in summary.recent_assistants[-max(1, args.message_limit) :]:
        print(f"- line {line} {ts or ''}: {text}")
    if not summary.recent_assistants:
        print("- None found.")

    print_heading("Recent Tools")
    for line, name, value in summary.recent_tools[-max(1, args.tool_limit) :]:
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

    print_heading("Resume Hint")
    print(f"- grok --resume {session_id}")
    if meta and meta.cwd:
        print(f"- Or from that project: grok --continue")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grok-home",
        default=str(default_grok_home()),
        help="Path to the Grok .grok directory (default: $GROK_HOME or ~/.grok).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    monitor_parser = sub.add_parser("monitor", help="List recent Grok sessions across workspaces")
    monitor_parser.add_argument("--recent", type=int, default=8)
    monitor_parser.add_argument("--cwd", help="Filter by exact working directory")
    monitor_parser.add_argument("--title", help="Case-insensitive session-title filter.")
    monitor_parser.add_argument("--query", help="Case-insensitive phrase to find in titles/transcripts.")
    monitor_parser.add_argument("--details", action="store_true")
    monitor_parser.add_argument("--text-limit", type=int, default=260)
    monitor_parser.set_defaults(func=monitor)

    inspect_parser = sub.add_parser("inspect", help="Summarize one Grok session by id")
    inspect_parser.add_argument("session_id")
    inspect_parser.add_argument("--message-limit", type=int, default=8)
    inspect_parser.add_argument("--tool-limit", type=int, default=20)
    inspect_parser.add_argument("--text-limit", type=int, default=420)
    inspect_parser.set_defaults(func=inspect)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
