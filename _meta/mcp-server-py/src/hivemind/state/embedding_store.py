"""Persistent, incremental embedding index for hybrid retrieval.

Computes and caches one dense vector per note. The on-disk cache
(``_meta/hive-embeddings.json``) is keyed by note path plus a content hash of
the embedded text, so only changed notes are re-embedded on rebuild. The cache
is invalidated automatically when the backend identity (name/dim) changes.

This file is derived data — it is gitignored, not committed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from typing import TYPE_CHECKING

from hivemind.scoring.embeddings import embed_text_for_note

if TYPE_CHECKING:
    from pathlib import Path

    from hivemind.model.note import Note
    from hivemind.scoring.embeddings import EmbeddingBackend

logger = logging.getLogger(__name__)


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


class EmbeddingStore:
    """Builds and caches note embeddings, and embeds ad-hoc queries.

    A single instance is constructed per server with a fixed backend. Call
    :meth:`index` with the current manifest notes to get a ``{path: vector}``
    mapping; repeated calls reuse the in-memory result while the note set is
    unchanged.
    """

    def __init__(self, hive_path: Path, backend: EmbeddingBackend) -> None:
        self._backend = backend
        self._path = hive_path / "_meta" / "hive-embeddings.json"
        self._lock = threading.Lock()
        self._vectors: dict[str, list[float]] = {}
        self._hashes: dict[str, str] = {}
        self._signature: tuple[str, int] = ("", 0)
        self._loaded = False

    @property
    def backend(self) -> EmbeddingBackend:
        return self._backend

    def _backend_signature(self) -> tuple[str, int]:
        return (self._backend.name, self._backend.dim)

    def _load_disk(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if (raw.get("backend"), raw.get("dim")) != self._backend_signature():
            logger.info("Embedding cache backend mismatch; rebuilding from scratch")
            return
        for path, entry in raw.get("vectors", {}).items():
            vec = entry.get("v")
            text_hash = entry.get("h")
            if isinstance(vec, list) and isinstance(text_hash, str):
                self._vectors[path] = [float(x) for x in vec]
                self._hashes[path] = text_hash

    def _save_disk(self) -> None:
        data = {
            "backend": self._backend.name,
            "dim": self._backend.dim,
            "vectors": {
                path: {"h": self._hashes[path], "v": self._vectors[path]}
                for path in self._vectors
            },
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError as exc:
            logger.warning("Could not persist embedding cache: %s", exc)

    def index(self, notes: list[Note]) -> dict[str, list[float]]:
        """Return ``{path: vector}`` for ``notes``, embedding only changed text."""
        with self._lock:
            self._load_disk()
            sig = self._backend_signature()
            if sig != self._signature:
                # Backend changed at runtime — drop any in-memory state.
                self._signature = sig

            wanted: dict[str, str] = {}
            to_embed_paths: list[str] = []
            to_embed_texts: list[str] = []
            for note in notes:
                text = embed_text_for_note(note)
                h = _text_hash(text)
                wanted[note.path] = h
                if self._hashes.get(note.path) != h or note.path not in self._vectors:
                    to_embed_paths.append(note.path)
                    to_embed_texts.append(text)

            changed = bool(to_embed_paths)
            if changed:
                vectors = self._backend.embed(to_embed_texts)
                for path, h, vec in zip(
                    to_embed_paths, (wanted[p] for p in to_embed_paths), vectors,
                    strict=False,
                ):
                    self._vectors[path] = vec
                    self._hashes[path] = h

            # Drop notes that no longer exist in the manifest.
            stale = set(self._vectors) - set(wanted)
            if stale:
                changed = True
                for path in stale:
                    self._vectors.pop(path, None)
                    self._hashes.pop(path, None)

            if changed:
                self._save_disk()

            return {p: self._vectors[p] for p in wanted if p in self._vectors}

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string into a dense vector."""
        if not query.strip():
            return []
        return self._backend.embed([query])[0]
