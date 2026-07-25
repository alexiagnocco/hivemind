"""Persistent, incremental chunk index for chunk-granularity retrieval.

Chunks every manifest note (heading-based splitter, see
:mod:`hivemind.chunking`) and caches the result in the gitignored
``_meta/hive-chunks.json``. The cache is incremental at two levels:

* **Chunking** is keyed by a content hash of the note file — an unchanged
  file reuses its cached chunk list without re-reading heading structure.
* **Embedding** is keyed by ``embed_hash = sha256(CCH header ‖ chunk)``.
  Headers carry note title/path/breadcrumb/tags, so a rename or retag changes
  the hash and re-embeds the affected chunks even if the body is unchanged.

The store works without an embedding backend (keyword-only chunk retrieval);
vectors are simply absent. This file is derived data — gitignored, never
committed. The manifest schema (v2, frozen) is untouched.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from hivemind.chunking import cch_header, chunk_note, embed_hash, embed_text_for_chunk

if TYPE_CHECKING:
    from pathlib import Path

    from hivemind.model.note import Note
    from hivemind.scoring.embeddings import EmbeddingBackend

logger = logging.getLogger(__name__)


def _file_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class ChunkRecord:
    """A chunk ready for retrieval: identity, display fields, and vector."""

    path: str
    anchor: str
    section: str
    text: str
    embed_hash: str
    vector: list[float] | None = None


class ChunkStore:
    """Builds and caches per-note chunks (+ optional vectors) incrementally."""

    def __init__(self, hive_path: Path, backend: EmbeddingBackend | None) -> None:
        self._hive_path = hive_path
        self._backend = backend
        self._path = hive_path / "_meta" / "hive-chunks.json"
        self._lock = threading.Lock()
        # path -> {"fileHash": str, "chunks": [{"anchor","section","text"}]}
        self._notes: dict[str, dict[str, Any]] = {}
        # embed_hash -> vector
        self._vectors: dict[str, list[float]] = {}
        self._loaded = False

    def _backend_signature(self) -> tuple[str, int]:
        if self._backend is None:
            return ("", 0)
        return (self._backend.name, self._backend.dim)

    def _load_disk(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        notes = raw.get("notes")
        if isinstance(notes, dict):
            for path, entry in notes.items():
                if isinstance(entry, dict) and isinstance(entry.get("chunks"), list):
                    self._notes[path] = entry
        sig = (raw.get("backend"), raw.get("dim"))
        if sig != self._backend_signature():
            logger.info("Chunk-vector cache backend mismatch; re-embedding")
            return
        vectors = raw.get("vectors")
        if isinstance(vectors, dict):
            for h, vec in vectors.items():
                if isinstance(vec, list):
                    self._vectors[h] = [float(x) for x in vec]

    def _save_disk(self) -> None:
        name, dim = self._backend_signature()
        data = {
            "backend": name,
            "dim": dim,
            "notes": self._notes,
            "vectors": self._vectors,
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError as exc:
            logger.warning("Could not persist chunk cache: %s", exc)

    def index(self, notes: list[Note]) -> dict[str, list[ChunkRecord]]:
        """Return ``{path: [ChunkRecord]}`` for ``notes``, incrementally.

        Re-chunks only notes whose file content changed; re-embeds only chunks
        whose ``embed_hash`` (header ‖ chunk) is not already cached.
        """
        with self._lock:
            self._load_disk()

            changed = False
            result: dict[str, list[ChunkRecord]] = {}
            wanted_hashes: set[str] = set()
            to_embed: list[tuple[str, str]] = []  # (embed_hash, embed_text)

            for note in notes:
                full = self._hive_path / note.path
                try:
                    source = full.read_text(encoding="utf-8")
                except OSError:
                    continue
                fhash = _file_hash(source)

                cached = self._notes.get(note.path)
                if cached is not None and cached.get("fileHash") == fhash:
                    chunk_dicts = cached["chunks"]
                else:
                    _fm, chunks = chunk_note(source)
                    chunk_dicts = [
                        {"anchor": c.anchor, "section": c.section, "text": c.text}
                        for c in chunks
                    ]
                    self._notes[note.path] = {"fileHash": fhash, "chunks": chunk_dicts}
                    changed = True

                records: list[ChunkRecord] = []
                for cd in chunk_dicts:
                    header = cch_header(
                        title=note.title or note.basename or "",
                        path=note.path,
                        section=str(cd.get("section", "")),
                        tags=list(note.tags),
                    )
                    text = str(cd.get("text", ""))
                    ehash = embed_hash(header, text)
                    wanted_hashes.add(ehash)
                    if self._backend is not None and ehash not in self._vectors:
                        to_embed.append((ehash, embed_text_for_chunk(header, text)))
                    records.append(
                        ChunkRecord(
                            path=note.path,
                            anchor=str(cd.get("anchor", "")),
                            section=str(cd.get("section", "")),
                            text=text,
                            embed_hash=ehash,
                        )
                    )
                result[note.path] = records

            if to_embed:
                # Dedupe while preserving order (identical chunks share vectors).
                unique: dict[str, str] = {}
                for ehash, text in to_embed:
                    unique.setdefault(ehash, text)
                assert self._backend is not None
                vectors = self._backend.embed(list(unique.values()))
                for ehash, vec in zip(unique.keys(), vectors, strict=False):
                    self._vectors[ehash] = vec
                changed = True

            # Prune notes gone from the manifest and vectors no longer wanted.
            wanted_paths = {n.path for n in notes}
            stale_notes = set(self._notes) - wanted_paths
            for path in stale_notes:
                self._notes.pop(path, None)
            stale_vectors = set(self._vectors) - wanted_hashes
            for h in stale_vectors:
                self._vectors.pop(h, None)
            if stale_notes or stale_vectors:
                changed = True

            if changed:
                self._save_disk()

            for records in result.values():
                for rec in records:
                    rec.vector = self._vectors.get(rec.embed_hash)

            return result

    def embed_query(self, query: str) -> list[float]:
        """Embed a query for chunk-cosine scoring ([] without a backend)."""
        if self._backend is None or not query.strip():
            return []
        return self._backend.embed([query])[0]
