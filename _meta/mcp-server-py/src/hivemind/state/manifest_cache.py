from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from hivemind.model.note import Manifest, dict_to_note

if TYPE_CHECKING:
    from pathlib import Path

    from hivemind.model.note import Note

logger = logging.getLogger(__name__)


class ManifestCache:
    def __init__(self, hive_path: Path) -> None:
        self._hive_path = hive_path
        self._manifest_path = hive_path / "_meta" / "hive-manifest.json"
        self._data: Manifest | None = None
        self._mtime_ns: int = 0

    def load(self) -> Manifest:
        try:
            stat = self._manifest_path.stat()
            mtime_ns = stat.st_mtime_ns
            if self._data is not None and self._mtime_ns == mtime_ns:
                return self._data

            raw = self._manifest_path.read_text(encoding="utf-8")
            parsed: dict[str, Any] = json.loads(raw)
            notes: list[Note] = [dict_to_note(n) for n in parsed.get("notes", [])]
            manifest = Manifest(
                version=parsed.get("version", ""),
                generated=parsed.get("generated", ""),
                hive_path=parsed.get("vault_path", str(self._hive_path)),
                note_count=parsed.get("note_count", len(notes)),
                notes=notes,
                stats=parsed.get("stats", {}),
            )
            self._data = manifest
            self._mtime_ns = mtime_ns
            return manifest
        except Exception as exc:
            return Manifest(
                error=f"Manifest not found or invalid: {exc}",
                hive_path=str(self._hive_path),
            )

    def invalidate(self) -> None:
        self._data = None
        self._mtime_ns = 0
