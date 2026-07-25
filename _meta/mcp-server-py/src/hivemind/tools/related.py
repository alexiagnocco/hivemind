from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hivemind.state.manifest_cache import ManifestCache


def build_related_response(cache: ManifestCache, *, note_ref: str) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    lookup = note_ref.removesuffix(".md").lower()
    target = None
    for n in manifest.notes:
        if (
            n.title.lower() == lookup
            or (n.basename or "").lower() == lookup
            or n.path.lower().endswith(f"/{lookup}.md")
        ):
            target = n
            break

    if target is None:
        return f"Note not found: {note_ref}"

    outbound_titles = set(target.outLinks or [])
    target_basename = target.basename or target.title

    inbound: list[dict[str, Any]] = []
    for n in manifest.notes:
        if n.path == target.path:
            continue
        if target_basename in (n.outLinks or []):
            inbound.append({"path": n.path, "title": n.title, "updated": n.updated or ""})

    outbound: list[dict[str, Any]] = []
    for n in manifest.notes:
        if (n.basename or n.title) in outbound_titles:
            outbound.append({"path": n.path, "title": n.title, "updated": n.updated or ""})

    return json.dumps(
        {
            "note": target.path,
            "outbound_count": len(outbound),
            "outbound_links": outbound,
            "inbound_count": len(inbound),
            "inbound_links": inbound,
        },
        indent=2,
    )
