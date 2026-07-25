from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from hivemind.model.note import slim_note, slim_note_to_dict

if TYPE_CHECKING:
    from hivemind.state.manifest_cache import ManifestCache


def build_manifest_response(cache: ManifestCache, *, slim: bool = True) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    if slim:
        notes = [slim_note_to_dict(slim_note(n)) for n in manifest.notes]
        result: dict[str, Any] = {
            "version": manifest.version,
            "generated": manifest.generated,
            "note_count": manifest.note_count,
            "stats": manifest.stats,
            "notes": notes,
        }
        return json.dumps(result, indent=2)

    from hivemind.model.note import note_to_dict

    result = {
        "version": manifest.version,
        "generated": manifest.generated,
        "hive_path": manifest.hive_path,
        "note_count": manifest.note_count,
        "stats": manifest.stats,
        "notes": [note_to_dict(n) for n in manifest.notes],
    }
    return json.dumps(result, indent=2)
