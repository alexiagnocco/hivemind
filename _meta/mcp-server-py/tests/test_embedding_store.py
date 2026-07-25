"""Tests for the persistent, incremental EmbeddingStore."""

from __future__ import annotations

from hivemind.scoring.embeddings import HashingEmbeddingBackend
from hivemind.state.embedding_store import EmbeddingStore


class CountingBackend:
    """Hashing backend that records how many texts it has embedded."""

    def __init__(self, dim: int = 32) -> None:
        self._inner = HashingEmbeddingBackend(dim=dim)
        self.name = self._inner.name
        self.dim = self._inner.dim
        self.embedded = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded += len(texts)
        return self._inner.embed(texts)


def test_index_returns_vector_per_note(tmp_path, make_note) -> None:
    store = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=16))
    notes = [make_note("a.md", title="alpha"), make_note("b.md", title="beta")]
    vectors = store.index(notes)
    assert set(vectors) == {"a.md", "b.md"}
    assert all(len(v) == 16 for v in vectors.values())


def test_persists_to_disk(tmp_path, make_note) -> None:
    backend = HashingEmbeddingBackend(dim=16)
    EmbeddingStore(tmp_path, backend).index([make_note("a.md", title="alpha")])
    assert (tmp_path / "_meta" / "hive-embeddings.json").is_file()


def test_reload_skips_recompute(tmp_path, make_note) -> None:
    notes = [make_note("a.md", title="alpha"), make_note("b.md", title="beta")]

    first = CountingBackend()
    EmbeddingStore(tmp_path, first).index(notes)
    assert first.embedded == 2

    # A fresh store with the same backend identity loads the cache from disk.
    second = CountingBackend()
    second.embedded = 0
    EmbeddingStore(tmp_path, second).index(notes)
    assert second.embedded == 0


def test_only_changed_notes_reembedded(tmp_path, make_note) -> None:
    backend = CountingBackend()
    store = EmbeddingStore(tmp_path, backend)
    store.index([make_note("a.md", title="alpha"), make_note("b.md", title="beta")])
    assert backend.embedded == 2

    # Change only b.md's text → exactly one re-embed.
    store.index([make_note("a.md", title="alpha"), make_note("b.md", title="BETA changed")])
    assert backend.embedded == 3


def test_stale_notes_dropped(tmp_path, make_note) -> None:
    backend = HashingEmbeddingBackend(dim=16)
    store = EmbeddingStore(tmp_path, backend)
    store.index([make_note("a.md", title="alpha"), make_note("b.md", title="beta")])
    vectors = store.index([make_note("a.md", title="alpha")])
    assert set(vectors) == {"a.md"}


def test_backend_mismatch_rebuilds(tmp_path, make_note) -> None:
    notes = [make_note("a.md", title="alpha")]
    EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=16)).index(notes)

    # Different dim → different signature → cache ignored, recomputed at new dim.
    vectors = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=32)).index(notes)
    assert len(vectors["a.md"]) == 32


def test_embed_query(tmp_path) -> None:
    store = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=16))
    assert store.embed_query("") == []
    assert len(store.embed_query("git rebase")) == 16
