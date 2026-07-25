"""Tests for the hive_context one-shot answer pack (Phase 3.3).

The context pack keeps the classic keys (Claude /boot compatibility) and adds
hits / related / retrievalId, with the retrieval routed through log_retrieval
so a single context call closes the MemRL loop.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from hivemind.config import Settings
from hivemind.rest.connection import ConnectionState
from hivemind.state.feedback import read_jsonl
from hivemind.state.manifest_cache import ManifestCache
from hivemind.state.utility import UtilityCache
from hivemind.tools.context import build_context_response

_MANIFEST = {
    "version": "2.0",
    "generated": "2026-07-01T00:00:00",
    "hive_path": "/tmp/vault",
    "note_count": 4,
    "stats": {},
    "notes": [
        {"path": "git-guide.md", "title": "Git rebase guide", "basename": "git-guide",
         "summary": "how to rebase branches", "updated": "2026-07-01", "inboundCount": 2,
         "outLinks": ["version-control"], "inboundLinks": ["version-control"]},
        {"path": "version-control.md", "title": "Version control", "basename": "version-control",
         "summary": "history management", "updated": "2026-07-01", "inboundCount": 1,
         "outLinks": ["git-guide"], "inboundLinks": ["git-guide"]},
        {"path": "sql-notes.md", "title": "SQL notes", "basename": "sql-notes",
         "summary": "query patterns", "updated": "2026-07-01", "inboundCount": 0},
        {"path": "memory/projects/demo.md", "title": "Project demo", "basename": "demo",
         "summary": "git workflow decisions", "updated": "2026-07-01", "inboundCount": 1},
    ],
}

_CLASSIC_KEYS = {
    "project_memory", "context_notes", "context_count",
    "recent_activity_7d", "inbox_count", "nudge",
}
_PACK_KEYS = {"hits", "related", "retrievalId"}


def _setup(tmp_path):
    meta = tmp_path / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "hive-manifest.json").write_text(json.dumps(_MANIFEST), encoding="utf-8")
    mem = tmp_path / "memory" / "projects"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "demo.md").write_text("# demo\n\nHandoff: continue phase 3\n", encoding="utf-8")
    settings = Settings(obsidian_api_key="k", hive_path=tmp_path)
    return ManifestCache(tmp_path), UtilityCache(tmp_path), settings


def _monitor(state=ConnectionState.CONNECTED):
    return SimpleNamespace(current_state=state)


def test_pack_keys_present_alongside_classic_keys(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=_monitor(),
            query="git",
        )
    )
    assert set(resp) >= _CLASSIC_KEYS
    assert set(resp) >= _PACK_KEYS


def test_hits_capped_at_five_and_minimal_shape(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=_monitor(),
            query="git",
        )
    )
    assert 1 <= len(resp["hits"]) <= 5
    for hit in resp["hits"]:
        assert set(hit) == {"path", "title", "score", "utility"}
    assert resp["hits"][0]["path"] in {"git-guide.md", "memory/projects/demo.md"}


def test_related_is_top_hit_neighbors_paths_only(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=_monitor(),
            query="rebase",
        )
    )
    # Top hit is git-guide.md; its only link neighbor is version-control.md.
    assert resp["hits"][0]["path"] == "git-guide.md"
    assert resp["related"] == ["version-control.md"]
    assert all(isinstance(p, str) for p in resp["related"])


def test_retrieval_id_logged_when_connected(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=_monitor(),
            project="demo", query="git",
        )
    )
    rid = resp["retrievalId"]
    assert rid
    events = read_jsonl(tmp_path / "_meta" / "feedback-log.jsonl")
    retrievals = [e for e in events if e.get("event") == "retrieval"]
    assert len(retrievals) == 1
    assert retrievals[0]["retrievalId"] == rid
    assert retrievals[0]["surfacedPaths"] == [h["path"] for h in resp["hits"]]
    # Retrieval counts bumped for surfaced notes (the MemRL signal).
    scores = utility_cache.load()
    assert scores[resp["hits"][0]["path"]].retrievals == 1


def test_no_log_when_disconnected(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache,
            monitor=_monitor(ConnectionState.DISCONNECTED),
            query="git",
        )
    )
    # A retrievalId is still returned for the caller, but nothing is logged.
    assert resp["retrievalId"]
    assert not (tmp_path / "_meta" / "feedback-log.jsonl").exists()


def test_fs_only_end_to_end_context_retrieval_id_to_feedback(tmp_path) -> None:
    # AC: hive_context returns a retrievalId that hive_feedback accepts
    # end-to-end under fs_only with REST down — the full FS-mode MemRL loop.
    from hivemind.tools.feedback import build_feedback_response

    cache, utility_cache, _ = _setup(tmp_path)
    settings = Settings(
        obsidian_api_key="k", hive_path=tmp_path, obsidian_fallback_mode="fs_only"
    )
    monitor = _monitor(ConnectionState.DISCONNECTED)

    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=monitor,
            project="demo", query="git",
        )
    )
    rid = resp["retrievalId"]
    assert rid and resp["hits"]
    events = read_jsonl(tmp_path / "_meta" / "feedback-log.jsonl")
    assert [e["retrievalId"] for e in events if e.get("event") == "retrieval"] == [rid]

    used = ",".join(h["path"] for h in resp["hits"][:2])
    fb = json.loads(
        build_feedback_response(
            utility_cache, settings, monitor=monitor,
            paths=used, helpful=True, retrieval_id=rid,
        )
    )
    assert "error" not in fb
    assert all(u["newUtility"] > 0.5 for u in fb["updated"])
    events = read_jsonl(tmp_path / "_meta" / "feedback-log.jsonl")
    feedback = [e for e in events if e.get("event") == "feedback"]
    assert len(feedback) == 1
    assert feedback[0]["retrievalId"] == rid


def test_no_query_no_project_pack_is_empty(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=_monitor(),
            domain="work",
        )
    )
    assert resp["hits"] == []
    assert resp["related"] == []
    assert resp["retrievalId"] == ""
    assert not (tmp_path / "_meta" / "feedback-log.jsonl").exists()


def test_classic_keys_unchanged_without_pack_inputs(tmp_path) -> None:
    # Legacy call shape (no utility cache/monitor) still works and keeps the
    # classic keys — the pack fields stay empty rather than erroring.
    cache, _utility_cache, settings = _setup(tmp_path)
    resp = json.loads(build_context_response(cache, settings, project="demo"))
    assert resp["project_memory"]["exists"] is True
    assert "continue phase 3" in resp["project_memory"]["recent_content"]
    assert resp["hits"] == []
    assert resp["retrievalId"] == ""


def test_default_response_stays_within_token_budget(tmp_path) -> None:
    cache, utility_cache, settings = _setup(tmp_path)
    resp = build_context_response(
        cache, settings,
        utility_cache=utility_cache, monitor=_monitor(),
        project="demo", query="git",
    )
    # ≤1200 tokens at defaults ≈ 4800 bytes (4 bytes/token heuristic).
    assert len(resp.encode("utf-8")) <= 4800


def _write_note_files(tmp_path) -> None:
    (tmp_path / "git-guide.md").write_text(
        "# Git rebase guide\n\n## Rebasing\nhow to rebase branches onto main\n",
        encoding="utf-8",
    )
    (tmp_path / "version-control.md").write_text(
        "# Version control\n\nhistory management\n", encoding="utf-8"
    )
    (tmp_path / "sql-notes.md").write_text(
        "# SQL notes\n\nquery patterns\n", encoding="utf-8"
    )


def test_chunk_store_upgrades_hits_to_chunks(tmp_path) -> None:
    from hivemind.state.chunk_store import ChunkStore

    cache, utility_cache, settings = _setup(tmp_path)
    _write_note_files(tmp_path)
    store = ChunkStore(tmp_path, None)
    resp = json.loads(
        build_context_response(
            cache, settings,
            utility_cache=utility_cache, monitor=_monitor(),
            chunk_store=store, query="rebase",
        )
    )
    assert resp["hits"]
    hit = resp["hits"][0]
    assert set(hit) == {"path", "anchor", "title", "section", "score", "excerpt", "utility"}
    assert hit["path"] == "git-guide.md"
    assert len(hit["excerpt"]) <= 200
    assert resp["retrievalId"]
    # Feedback log joins on parent note paths.
    events = read_jsonl(tmp_path / "_meta" / "feedback-log.jsonl")
    retrieval = next(e for e in events if e.get("event") == "retrieval")
    assert "git-guide.md" in retrieval["surfacedPaths"]
    # Budget holds with chunk hits too.
    raw = build_context_response(
        cache, settings,
        utility_cache=utility_cache, monitor=_monitor(),
        chunk_store=store, project="demo", query="git",
    )
    assert len(raw.encode("utf-8")) <= 4800
