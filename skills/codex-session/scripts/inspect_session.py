#!/usr/bin/env python3
"""Summarize a local Codex Desktop session transcript by session id."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CODEX_HOME = Path.home() / ".codex"
SESSION_INDEX = CODEX_HOME / "session_index.jsonl"
SESSIONS_DIR = CODEX_HOME / "sessions"
SHELL_SNAPSHOTS_DIR = CODEX_HOME / "shell_snapshots"


SECRET_PATTERNS = [
    re.compile(r"(?i)(x-fast-service-key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)"),
    re.compile(r"(?i)(service[_-]?key|api[_-]?key|token|secret|password|passwd|pwd)([=:]\s*)([^\s\"']+)"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd)([=:]\s*)([^\s\"']+)"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"sm_[A-Za-z0-9_-]{12,}"),
]

SPEC_PATTERN = re.compile(r"\b(?:spec|spec-archive)/[A-Za-z0-9._/\[\]$-]+")
PATH_PATTERN = re.compile(
    r"\b(?:src|tests|scripts|spec|spec-archive|docs|\.agents|\.codex|\.claude)(?:/|\\)"
    r"[A-Za-z0-9._/\\\[\]$:@+-]+"
)

try:
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, OSError):
    pass


def redact(text: str) -> str:
    value = text
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)(bearer"):
            value = pattern.sub(r"\1[REDACTED]", value)
        elif pattern.pattern.startswith("sk-") or pattern.pattern.startswith("sm_"):
            value = pattern.sub("[REDACTED]", value)
        elif "x-fast-service-key" in pattern.pattern:
            value = pattern.sub(r"\1[REDACTED]", value)
        else:
            value = pattern.sub(r"\1\2[REDACTED]", value)
    return value


def truncate(text: str, limit: int) -> str:
    text = redact(text.replace("\r\n", "\n"))
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 20)].rstrip() + " ... [truncated]"


def parse_json_maybe(value: str) -> Any | None:
    try:
        return json.loads(value)
    except Exception:
        return None


def extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("input_text") or item.get("output_text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                events.append({"type": "parse_error", "line": line_number, "raw": line})
                continue
            event["_line"] = line_number
            events.append(event)
    return events


def find_index_entries(session_id: str) -> list[dict[str, Any]]:
    if not SESSION_INDEX.exists():
        return []
    matches: list[dict[str, Any]] = []
    for event in read_jsonl(SESSION_INDEX):
        if event.get("id") == session_id:
            matches.append(event)
    return matches


def find_transcripts(session_id: str) -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.rglob(f"*{session_id}.jsonl"))


def find_shell_snapshots(session_id: str) -> list[Path]:
    if not SHELL_SNAPSHOTS_DIR.exists():
        return []
    return sorted(SHELL_SNAPSHOTS_DIR.glob(f"{session_id}.*"))


def remember_refs(summary: dict[str, Any], text: str) -> None:
    if not text:
        return
    summary["referenced_specs"].update(SPEC_PATTERN.findall(text))
    summary["referenced_paths"].update(PATH_PATTERN.findall(text))


def summarize_transcript(path: Path, message_limit: int, command_limit: int, text_limit: int) -> dict[str, Any]:
    events = read_jsonl(path)
    summary: dict[str, Any] = {
        "path": str(path),
        "event_count": len(events),
        "metadata": [],
        "goals": [],
        "user_messages": [],
        "assistant_messages": [],
        "task_complete": [],
        "commands": [],
        "referenced_paths": set(),
        "referenced_specs": set(),
    }

    for event in events:
        etype = event.get("type")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        line = event.get("_line")

        if etype == "session_meta":
            meta = payload.copy()
            summary["metadata"].append(meta)

        if etype == "response_item":
            item_type = payload.get("type")

            if item_type == "message":
                role = payload.get("role")
                text = extract_text_from_content(payload.get("content"))
                if role == "user":
                    summary["user_messages"].append((line, text))
                elif role == "assistant":
                    phase = payload.get("phase")
                    summary["assistant_messages"].append((line, phase, text))
                remember_refs(summary, text)

            if item_type == "function_call":
                name = payload.get("name")
                arguments = payload.get("arguments")
                command_text = ""
                parsed = parse_json_maybe(arguments) if isinstance(arguments, str) else None
                if isinstance(parsed, dict) and isinstance(parsed.get("cmd"), str):
                    command_text = parsed["cmd"]
                elif isinstance(arguments, str):
                    command_text = arguments
                if command_text:
                    summary["commands"].append((line, name, command_text))
                    remember_refs(summary, command_text)

            if item_type == "function_call_output":
                output = payload.get("output")
                if isinstance(output, str) and '"goal"' in output:
                    parsed = parse_json_maybe(output)
                    if isinstance(parsed, dict) and isinstance(parsed.get("goal"), dict):
                        goal = parsed["goal"]
                        summary["goals"].append((line, goal))
                        remember_refs(summary, str(goal.get("objective", "")))

            if item_type == "custom_tool_call":
                name = payload.get("name")
                if name:
                    summary["commands"].append((line, name, f"<custom tool: {name}>"))
                tool_input = payload.get("input")
                if isinstance(tool_input, str):
                    remember_refs(summary, tool_input)

        if etype == "event_msg" and payload.get("type") == "task_complete":
            text = payload.get("last_agent_message", "")
            summary["task_complete"].append((line, text))
            remember_refs(summary, text)

    summary["user_messages"] = summary["user_messages"][-message_limit:]
    summary["assistant_messages"] = summary["assistant_messages"][-message_limit:]
    summary["task_complete"] = summary["task_complete"][-message_limit:]
    summary["commands"] = summary["commands"][-command_limit:]
    summary["referenced_specs"] = sorted(summary["referenced_specs"])
    summary["referenced_paths"] = sorted(summary["referenced_paths"])
    summary["text_limit"] = text_limit
    return summary


def print_heading(title: str) -> None:
    print(f"\n## {title}")


def print_bullets(items: list[str], empty: str = "None found.") -> None:
    if not items:
        print(f"- {empty}")
        return
    for item in items:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_id", help="Codex Desktop session/thread id")
    parser.add_argument("--message-limit", type=int, default=8)
    parser.add_argument("--command-limit", type=int, default=24)
    parser.add_argument("--text-limit", type=int, default=900)
    args = parser.parse_args()

    session_id = args.session_id.strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{20,}", session_id):
        raise SystemExit(f"Invalid-looking session id: {session_id}")

    print(f"# Codex Session Summary: {session_id}")

    print_heading("Index Entries")
    index_entries = find_index_entries(session_id)
    if index_entries:
        for entry in index_entries:
            print(f"- {entry.get('updated_at', '?')} | {entry.get('thread_name', '(unnamed)')}")
    else:
        print("- No matching session_index.jsonl entries.")

    transcripts = find_transcripts(session_id)
    print_heading("Transcript Files")
    print_bullets([str(path) for path in transcripts])

    snapshots = find_shell_snapshots(session_id)
    print_heading("Shell Snapshots")
    if snapshots:
        print("- Shell snapshots exist but are not read by this helper because they may contain secrets.")
        for path in snapshots:
            print(f"- {path}")
    else:
        print("- None found.")

    if not transcripts:
        return 1

    for transcript in transcripts:
        summary = summarize_transcript(
            transcript,
            message_limit=max(1, args.message_limit),
            command_limit=max(1, args.command_limit),
            text_limit=max(120, args.text_limit),
        )
        text_limit = summary["text_limit"]

        print_heading(f"Transcript: {transcript}")
        print(f"- Events: {summary['event_count']}")

        print_heading("Metadata")
        if summary["metadata"]:
            for meta in summary["metadata"][:3]:
                payload = meta.get("payload") if isinstance(meta.get("payload"), dict) else meta
                fields = []
                for key in ("id", "timestamp", "cwd", "originator", "cli_version"):
                    if payload.get(key):
                        fields.append(f"{key}={payload[key]}")
                git = payload.get("git")
                if isinstance(git, dict):
                    if git.get("branch"):
                        fields.append(f"branch={git['branch']}")
                    if git.get("commit_hash"):
                        fields.append(f"commit={git['commit_hash']}")
                print(f"- {'; '.join(fields) if fields else truncate(json.dumps(payload), text_limit)}")
        else:
            print("- No session_meta event found.")

        print_heading("Goal Events")
        if summary["goals"]:
            for line, goal in summary["goals"]:
                objective = truncate(str(goal.get("objective", "")), text_limit)
                print(
                    f"- line {line}: status={goal.get('status')} "
                    f"tokens={goal.get('tokensUsed')} objective={objective}"
                )
        else:
            print("- No create_goal/update_goal output found.")

        print_heading("Recent User Messages")
        if summary["user_messages"]:
            for line, text in summary["user_messages"]:
                print(f"- line {line}: {truncate(text, text_limit)}")
        else:
            print("- None found.")

        print_heading("Recent Assistant Messages")
        if summary["assistant_messages"]:
            for line, phase, text in summary["assistant_messages"]:
                label = f"line {line}"
                if phase:
                    label += f" phase={phase}"
                print(f"- {label}: {truncate(text, text_limit)}")
        else:
            print("- None found.")

        print_heading("Task Complete Messages")
        if summary["task_complete"]:
            for line, text in summary["task_complete"]:
                print(f"- line {line}: {truncate(text, text_limit)}")
        else:
            print("- None found.")

        print_heading("Referenced Specs")
        print_bullets(summary["referenced_specs"][:80])

        print_heading("Referenced Paths")
        print_bullets(summary["referenced_paths"][:80])

        print_heading("Recent Commands / Tools")
        if summary["commands"]:
            for line, name, cmd in summary["commands"]:
                print(f"- line {line} {name}: {truncate(cmd, text_limit)}")
        else:
            print("- None found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
