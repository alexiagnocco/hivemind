#!/usr/bin/env python3
"""Log session metadata to hive session-log.jsonl.

Called by the global Stop hook at the end of every Claude Code session.
Scans ALL project directories for sessions, not just the current project.

Usage: python log-session.py [--backfill]
  No args:    Log the most recent session for the current project
  --backfill: Scan all projects and log any sessions not yet in session-log.jsonl
"""

import json
import os
import sys
import glob
from datetime import datetime
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude" / "projects"
# Hive root is configurable via HIVE_PATH; defaults to ~/hive.
HIVE_META = Path(os.environ.get("HIVE_PATH", str(Path.home() / "hive"))) / "_meta"
SESSION_LOG = HIVE_META / "session-log.jsonl"
EXTRACT_MANIFEST = HIVE_META / "session-extract-manifest.json"


def cwd_to_project_dir(cwd: str) -> str:
    """Convert a working directory path to Claude's project directory name."""
    # Normalize to forward slashes
    cwd = cwd.replace("\\", "/")
    # Handle UNC paths: //server/share -> --server-share
    if cwd.startswith("//"):
        return "-" + cwd[1:].replace("/", "-")
    # Handle drive paths: C:/Users/... -> C--Users-...
    # or /c/Users/... -> C--Users-...
    if len(cwd) >= 2 and cwd[1] == ":":
        return cwd[0] + "-" + cwd[2:].replace("/", "-")
    if len(cwd) >= 3 and cwd[0] == "/" and cwd[2] == "/":
        return cwd[1].upper() + "-" + cwd[2:].replace("/", "-")
    return cwd.replace("/", "-")


def load_logged_sessions() -> set:
    """Load session IDs already in session-log.jsonl."""
    logged = set()
    if SESSION_LOG.exists():
        with open(SESSION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        logged.add(obj.get("sessionId", ""))
                    except json.JSONDecodeError:
                        pass
    return logged


def load_processed_sessions() -> set:
    """Load session IDs from extract manifest (already mined)."""
    processed = set()
    if EXTRACT_MANIFEST.exists():
        with open(EXTRACT_MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)
            for entry in data.get("processed", []):
                processed.add(entry.get("sessionId", ""))
    return processed


def extract_session_metadata(jsonl_path: Path) -> dict | None:
    """Extract metadata from a session JSONL file."""
    size_bytes = jsonl_path.stat().st_size
    if size_bytes < 1000:
        return None

    session_id = jsonl_path.stem
    first_ts = None
    last_ts = None
    user_msg_count = 0
    asst_msg_count = 0
    is_scheduled = False
    first_user_text = ""
    project_dir = jsonl_path.parent.name

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    t = obj.get("type", "")
                    ts = obj.get("timestamp", "")

                    if ts and not first_ts:
                        first_ts = ts
                    if ts:
                        last_ts = ts

                    if t == "user":
                        user_msg_count += 1
                        if user_msg_count == 1:
                            msg = obj.get("message", "")
                            text = ""
                            if isinstance(msg, str):
                                text = msg
                            elif isinstance(msg, dict):
                                c = msg.get("content", "")
                                if isinstance(c, str):
                                    text = c
                                elif isinstance(c, list):
                                    for b in c:
                                        if isinstance(b, dict) and b.get("type") == "text":
                                            text = b.get("text", "")
                                            break
                            first_user_text = text[:200]
                            if "<scheduled-task" in first_user_text:
                                is_scheduled = True

                    elif t == "assistant":
                        asst_msg_count += 1

                except json.JSONDecodeError:
                    pass
    except Exception:
        return None

    if user_msg_count == 0:
        return None

    # Determine if mining is recommended
    mine_recommended = (
        not is_scheduled
        and size_bytes > 50000
        and user_msg_count > 5
    )

    return {
        "sessionId": session_id,
        "projectDir": project_dir,
        "startTime": first_ts[:19] if first_ts else None,
        "endTime": last_ts[:19] if last_ts else None,
        "date": first_ts[:10] if first_ts else datetime.now().strftime("%Y-%m-%d"),
        "sizeKB": size_bytes // 1024,
        "userMessages": user_msg_count,
        "assistantMessages": asst_msg_count,
        "isScheduledTask": is_scheduled,
        "mineRecommended": mine_recommended,
        "topicHint": first_user_text[:120].replace("\n", " ").strip() if not is_scheduled else "scheduled-task",
        "loggedAt": datetime.now().isoformat()
    }


def append_to_log(entry: dict):
    """Append a session entry to session-log.jsonl."""
    SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_current_project(cwd: str):
    """Log the most recent session for the current project directory."""
    project_name = cwd_to_project_dir(cwd)
    project_path = CLAUDE_DIR / project_name

    if not project_path.exists():
        return

    # Find most recently modified JSONL
    jsonl_files = sorted(
        project_path.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not jsonl_files:
        return

    logged = load_logged_sessions()
    latest = jsonl_files[0]

    if latest.stem in logged:
        return

    meta = extract_session_metadata(latest)
    if meta:
        append_to_log(meta)


def backfill_all_projects():
    """Scan all project directories and log any unlogged sessions."""
    if not CLAUDE_DIR.exists():
        print("No Claude projects directory found.")
        return

    logged = load_logged_sessions()
    processed = load_processed_sessions()
    skip = logged | processed

    new_count = 0
    skip_count = 0

    for project_dir in sorted(CLAUDE_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        # Skip worktree directories
        if "worktree" in project_dir.name:
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            sid = jsonl_file.stem
            if sid in skip:
                skip_count += 1
                continue

            meta = extract_session_metadata(jsonl_file)
            if meta:
                append_to_log(meta)
                skip.add(sid)
                new_count += 1

    print(f"Backfill complete: {new_count} sessions logged, {skip_count} skipped (already logged/processed)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--backfill":
        backfill_all_projects()
    elif len(sys.argv) > 1:
        log_current_project(sys.argv[1])
    else:
        log_current_project(os.getcwd())
