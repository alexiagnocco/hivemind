"""hive_session_check tool — post-session validation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from hivemind.fs.paths import is_system_note

if TYPE_CHECKING:
    from hivemind.state.manifest_cache import ManifestCache


def build_session_check_response(
    cache: ManifestCache,
    *,
    project: str = "",
    since_minutes: int = 120,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    cutoff = (datetime.now(UTC) - timedelta(minutes=since_minutes)).isoformat()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    issues: list[str] = []

    new_notes = [
        n for n in manifest.notes
        if (n.lastModified or "") >= cutoff and (n.created or "") >= today
    ]
    modified_notes = [
        n for n in manifest.notes
        if (n.lastModified or "") >= cutoff and (n.created or "") < today
    ]

    memory_updated = False
    if project:
        mem_path = f"memory/projects/{project}.md"
        memory_updated = any(
            n.path == mem_path and (n.lastModified or "") >= cutoff
            for n in manifest.notes
        )
        if not memory_updated:
            issues.append(f"Project memory for '{project}' was not updated this session.")

    orphan_count = 0
    for n in new_notes:
        if n.inboundCount == 0 and not is_system_note(n.path):
            orphan_count += 1
            issues.append(f"Orphan note: {n.path}")

    stale_updated = 0
    for n in modified_notes:
        if (n.updated or "") != today:
            stale_updated += 1
            issues.append(f"Stale updated: field in {n.path}")

    if not new_notes and not modified_notes:
        issues.append("No vault notes created or modified this session.")

    score = 0
    if new_notes or modified_notes:
        score += 40
    if memory_updated or not project:
        score += 20
    if orphan_count == 0:
        score += 20
    if stale_updated == 0:
        score += 20

    return json.dumps({
        "score": score,
        "notes_created": len(new_notes),
        "notes_modified": len(modified_notes),
        "project_memory_updated": memory_updated,
        "orphan_count": orphan_count,
        "stale_updated_count": stale_updated,
        "issues": issues,
        "healthy": score >= 80,
    }, indent=2)
