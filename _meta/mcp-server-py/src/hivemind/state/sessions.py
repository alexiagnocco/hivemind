"""Session-log JSONL reader + extract-manifest reader for unmined-session detection."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def read_session_log(hive_path: Path) -> list[dict[str, Any]]:
    """Read _meta/session-log.jsonl and return parsed entries."""
    log_path = hive_path / "_meta" / "session-log.jsonl"
    if not log_path.exists():
        return []
    results: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            results.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return results


_MANIFEST_META_KEYS = frozenset({"processed", "version"})
_SESSION_ID_MIN_LEN = 36  # UUID length


def read_processed_session_ids(hive_path: Path) -> set[str]:
    """Read _meta/session-extract-manifest.json and return processed session IDs.

    Supports two manifest formats:
    - ``processed`` array with ``{"sessionId": "..."}`` entries
    - Top-level keys where the key itself is the session ID
    """
    manifest_path = hive_path / "_meta" / "session-extract-manifest.json"
    if not manifest_path.exists():
        return set()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, KeyError):
        return set()

    ids: set[str] = set()

    for entry in data.get("processed", []):
        sid = entry.get("sessionId")
        if sid:
            ids.add(str(sid))

    for key in data:
        if key not in _MANIFEST_META_KEYS and len(key) >= _SESSION_ID_MIN_LEN:
            ids.add(key)

    return ids
