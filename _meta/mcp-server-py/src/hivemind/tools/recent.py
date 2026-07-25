from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from hivemind.model.note import slim_note, slim_note_to_dict

if TYPE_CHECKING:
    from hivemind.state.manifest_cache import ManifestCache


def build_recent_response(
    cache: ManifestCache,
    *,
    days: int = 7,
    domain: str = "",
    limit: int = 50,
    slim: bool = True,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    cutoff = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    filtered = [
        n
        for n in manifest.notes
        if (n.updated or "") >= cutoff and (not domain or n.domain == domain)
    ]
    filtered.sort(key=lambda n: n.updated or "", reverse=True)

    capped = filtered[:limit]
    output: list[dict[str, Any]]
    if slim:
        output = [slim_note_to_dict(slim_note(n)) for n in capped]
    else:
        from hivemind.model.note import note_to_dict

        output = [note_to_dict(n) for n in capped]

    if not output:
        return f"No notes modified in the last {days} days."

    return json.dumps(
        {"notes": output, "count": len(output), "total": len(filtered)},
        indent=2,
    )
