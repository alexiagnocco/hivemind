from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UtilityEntry:
    utility: float = 0.5
    retrievals: int = 0
    citations: int = 0
    lastUpdated: str = ""


UtilityScores = dict[str, UtilityEntry]


class UtilityCache:
    def __init__(self, hive_path: Path) -> None:
        self._path = hive_path / "_meta" / "utility-scores.json"
        self._data: UtilityScores | None = None
        self._mtime_ns: int = 0
        self._lock = threading.Lock()

    def load(self) -> UtilityScores:
        with self._lock:
            try:
                stat = self._path.stat()
                mtime_ns = stat.st_mtime_ns
                if self._data is not None and self._mtime_ns == mtime_ns:
                    return self._data

                raw: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))
                scores: UtilityScores = {}
                for path, entry in raw.items():
                    scores[path] = UtilityEntry(
                        utility=entry.get("utility", 0.5),
                        retrievals=entry.get("retrievals", 0),
                        citations=entry.get("citations", 0),
                        lastUpdated=entry.get("lastUpdated", ""),
                    )
                self._data = scores
                self._mtime_ns = mtime_ns
                return scores
            except Exception:
                return {}

    def save(self, scores: UtilityScores) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data: dict[str, Any] = {}
            for path, entry in scores.items():
                data[path] = {
                    "utility": entry.utility,
                    "retrievals": entry.retrievals,
                    "citations": entry.citations,
                    "lastUpdated": entry.lastUpdated,
                }
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp, self._path)
            self._data = None
