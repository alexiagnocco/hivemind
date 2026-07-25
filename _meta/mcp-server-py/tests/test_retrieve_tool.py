"""Integration test for build_retrieve_response — the hive_retrieve tool surface.

Exercises the full path: ManifestCache → EmbeddingStore (hashing) → hybrid
retrieve → JSON response, with a disconnected monitor so no MemRL log is written.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from hivemind.config import Settings
from hivemind.rest.connection import ConnectionState
from hivemind.scoring.embeddings import HashingEmbeddingBackend
from hivemind.state.embedding_store import EmbeddingStore
from hivemind.state.manifest_cache import ManifestCache
from hivemind.state.utility import UtilityCache
from hivemind.tools.retrieve import build_retrieve_response

_MANIFEST = {
    "version": "2.0",
    "generated": "2026-05-28T00:00:00",
    "hive_path": "/tmp/vault",
    "note_count": 3,
    "stats": {},
    "notes": [
        {"path": "git-guide.md", "title": "Git rebase guide", "basename": "git-guide",
         "summary": "how to rebase branches", "updated": "2026-05-20", "inboundCount": 2},
        {"path": "sql-notes.md", "title": "SQL notes", "basename": "sql-notes",
         "summary": "query patterns", "updated": "2026-05-20", "inboundCount": 2},
        {"path": "memory/projects/p.md", "title": "Project P", "basename": "p",
         "summary": "git workflow decisions", "updated": "2026-05-20", "inboundCount": 1},
    ],
}


def _write_manifest(hive_path) -> None:
    meta = hive_path / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "hive-manifest.json").write_text(json.dumps(_MANIFEST), encoding="utf-8")


def _settings(hive_path) -> Settings:
    return Settings(
        obsidian_api_key="k",
        hive_path=hive_path,
        hivemind_embeddings_backend="hashing",
        hivemind_embeddings_dim=64,
    )


def _disconnected():
    return SimpleNamespace(current_state=ConnectionState.DISCONNECTED)


def test_hybrid_mode_reported(tmp_path) -> None:
    _write_manifest(tmp_path)
    store = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=64))
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=store,
            query="git",
            max_results=5,
        )
    )
    assert resp["mode"] == "hybrid"
    assert resp["count"] >= 1
    assert "retrievalId" in resp
    paths = [r["path"] for r in resp["results"]]
    assert "git-guide.md" in paths
    # Embedding cache was written as a side effect.
    assert (tmp_path / "_meta" / "hive-embeddings.json").is_file()


def test_keyword_mode_without_store(tmp_path) -> None:
    _write_manifest(tmp_path)
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=None,
            query="git",
            max_results=5,
            detail="full",
        )
    )
    assert resp["mode"] == "keyword"
    # Per-result mode is part of the full envelope only.
    assert all(r["mode"] == "keyword" for r in resp["results"])


def test_default_standard_detail_keeps_skill_parsed_keys(tmp_path) -> None:
    # .claude/skills/{recall,boot} render "[[title]] — summary (updated) [status]
    # (utility)" from default hive_retrieve output; the standard tier must keep
    # those keys and drop the per-component score internals.
    _write_manifest(tmp_path)
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=None,
            query="git",
            max_results=5,
        )
    )
    assert "retrievalId" in resp
    top = resp["results"][0]
    assert {"path", "title", "score", "summary", "updated", "utility"} <= set(top)
    assert top["summary"]
    assert not {"matchScore", "freshnessScore", "connectivityScore", "baseScore"} & set(top)


def _write_note_files(hive_path) -> None:
    (hive_path / "git-guide.md").write_text(
        "# Git rebase guide\n\n## Rebasing\nhow to rebase branches onto main\n\n"
        "## Conflicts\nresolving rebase conflicts step by step\n",
        encoding="utf-8",
    )
    (hive_path / "sql-notes.md").write_text(
        "# SQL notes\n\n## Queries\nquery patterns and joins\n", encoding="utf-8"
    )
    mem = hive_path / "memory" / "projects"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "p.md").write_text("# Project P\n\ngit workflow decisions\n", encoding="utf-8")


def test_chunk_granularity_returns_anchored_hits(tmp_path) -> None:
    from hivemind.state.chunk_store import ChunkStore

    _write_manifest(tmp_path)
    _write_note_files(tmp_path)
    store = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=64))
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            chunk_store=store,
            query="rebase",
            granularity="chunk",
        )
    )
    assert resp["granularity"] == "chunk"
    assert resp["mode"] == "hybrid"
    assert 1 <= resp["count"] <= 5
    hit = resp["results"][0]
    assert set(hit) == {"path", "anchor", "title", "section", "score", "excerpt", "utility"}
    assert hit["path"] == "git-guide.md"
    assert hit["anchor"] in {"Rebasing", "Conflicts", ""}
    assert len(hit["excerpt"]) <= 403  # 400 chars + ellipsis
    # Chunk cache persisted to the gitignored derived-data location.
    assert (tmp_path / "_meta" / "hive-chunks.json").is_file()


def test_chunk_granularity_caps_results_at_five(tmp_path) -> None:
    from hivemind.state.chunk_store import ChunkStore

    _write_manifest(tmp_path)
    _write_note_files(tmp_path)
    store = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=64))
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            chunk_store=store,
            query="git",
            max_results=50,
            granularity="chunk",
        )
    )
    assert resp["count"] <= 5


def test_chunk_granularity_requires_query(tmp_path) -> None:
    from hivemind.state.chunk_store import ChunkStore

    _write_manifest(tmp_path)
    _write_note_files(tmp_path)
    store = ChunkStore(tmp_path, None)
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            chunk_store=store,
            query="",
            granularity="chunk",
        )
    )
    assert "error" in resp


def test_unknown_granularity_rejected(tmp_path) -> None:
    _write_manifest(tmp_path)
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            query="git",
            granularity="paragraph",
        )
    )
    assert "error" in resp


def test_empty_query_stays_keyword_even_with_store(tmp_path) -> None:
    _write_manifest(tmp_path)
    store = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=64))
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=store,
            query="",
            project="p",
            max_results=5,
        )
    )
    # Dense path only activates for text queries.
    assert resp["mode"] == "keyword"
