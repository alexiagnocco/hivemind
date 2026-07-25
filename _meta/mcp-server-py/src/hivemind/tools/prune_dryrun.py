"""hive_prune_dryrun tool — count prune candidates by category."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from hivemind.fs.paths import is_system_note

if TYPE_CHECKING:
    from hivemind.model.note import Note
    from hivemind.state.manifest_cache import ManifestCache


_ELIGIBLE_STALE_PREFIXES = ("10-projects/", "30-resources/")
_COMPLETED_STATUSES = frozenset(("done", "archived"))


def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _days_since(date_str: str, now: datetime) -> int | None:
    dt = _parse_date(date_str)
    if dt is None:
        return None
    return (now - dt).days


def _candidate_dict(note: Note, category: str, reason: str) -> dict[str, Any]:
    return {
        "path": note.path,
        "title": note.title,
        "category": category,
        "reason": reason,
        "updated": note.updated,
        "status": note.status,
        "inbound_links": note.inboundCount,
    }


def build_prune_dryrun_response(
    cache: ManifestCache,
    *,
    stale_days: int = 30,
    inbox_days: int = 7,
    meta_days: int = 14,
    include_candidates: bool = False,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return json.dumps({"error": manifest.error})

    now = datetime.now(UTC)
    candidates: list[dict[str, Any]] = []
    counts = {"stale": 0, "completed": 0, "empty": 0, "inbox_aging": 0, "meta_artifact": 0}

    for note in manifest.notes:
        if is_system_note(note.path):
            continue

        # Stale: old notes in project/resource folders
        if note.path.startswith(_ELIGIBLE_STALE_PREFIXES):
            age = _days_since(note.updated or note.created, now)
            if age is not None and age > stale_days:
                counts["stale"] += 1
                if include_candidates:
                    candidates.append(
                        _candidate_dict(note, "stale", f"{age}d since last update")
                    )
                continue

        # Completed: done/archived still in 10-projects/
        if note.path.startswith("10-projects/") and note.status in _COMPLETED_STATUSES:
            counts["completed"] += 1
            if include_candidates:
                candidates.append(
                    _candidate_dict(note, "completed", f"status={note.status}")
                )
            continue

        # Empty: very small notes with no summary
        if note.sizeBytes > 0 and note.sizeBytes < 150 and not note.summary.strip():
            counts["empty"] += 1
            if include_candidates:
                candidates.append(
                    _candidate_dict(note, "empty", f"{note.sizeBytes}B, no summary")
                )
            continue

        # Inbox aging: old inbox items
        if note.path.startswith("00-inbox/"):
            age = _days_since(note.updated or note.created, now)
            if age is not None and age > inbox_days:
                counts["inbox_aging"] += 1
                if include_candidates:
                    candidates.append(
                        _candidate_dict(note, "inbox_aging", f"{age}d in inbox")
                    )
                continue

        # Meta artifacts: old accepted/rejected proposals
        if note.path.startswith("_meta/") and note.status in ("accepted", "rejected"):
            age = _days_since(note.updated or note.created, now)
            if age is not None and age > meta_days:
                counts["meta_artifact"] += 1
                if include_candidates:
                    candidates.append(
                        _candidate_dict(note, "meta_artifact", f"{age}d, status={note.status}")
                    )

    total = sum(counts.values())
    result: dict[str, Any] = {"total": total, "counts": counts}
    if include_candidates:
        result["candidates"] = candidates

    return json.dumps(result, indent=2)
