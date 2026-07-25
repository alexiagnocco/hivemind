"""Phase 4 — MemRL writes under FS-only fallback (memrl_writes_allowed).

fs_only reads the live filesystem, so the stale-snapshot risk that gates MemRL
writes on REST CONNECTED does not apply: feedback and retrieval logging must
work. Under auto with REST down, writes still defer.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from hivemind.config import Settings
from hivemind.rest.connection import ConnectionState
from hivemind.scoring.memrl import memrl_writes_allowed
from hivemind.state.manifest_cache import ManifestCache
from hivemind.state.utility import UtilityCache
from hivemind.tools.feedback import build_feedback_response
from hivemind.tools.retrieve import build_retrieve_response


def _settings(hive_path: Any, mode: str) -> Settings:
    return Settings(
        obsidian_api_key="k",
        hive_path=hive_path,
        obsidian_fallback_mode=mode,
        hivemind_embeddings_backend="none",
    )


def _monitor(state: ConnectionState) -> SimpleNamespace:
    return SimpleNamespace(current_state=state)


# ---------------------------------------------------------------------------
# The shared helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "state", "allowed"),
    [
        ("fs_only", ConnectionState.DISCONNECTED, True),
        ("fs_only", ConnectionState.UNCONFIGURED, True),
        ("fs_only", ConnectionState.CONNECTED, True),
        ("auto", ConnectionState.CONNECTED, True),
        ("auto", ConnectionState.DISCONNECTED, False),
        ("auto", ConnectionState.DEGRADED, False),
        ("auto", ConnectionState.UNCONFIGURED, False),
        ("rest_only", ConnectionState.DISCONNECTED, False),
    ],
)
def test_memrl_writes_allowed(
    tmp_path: Any, mode: str, state: ConnectionState, allowed: bool
) -> None:
    settings = _settings(tmp_path, mode)
    assert memrl_writes_allowed(settings, _monitor(state)) is allowed  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# hive_feedback gate
# ---------------------------------------------------------------------------


def _feedback(hive_path: Any, mode: str, state: ConnectionState) -> dict[str, Any]:
    return json.loads(
        build_feedback_response(
            UtilityCache(hive_path),
            _settings(hive_path, mode),
            monitor=_monitor(state),  # type: ignore[arg-type]
            paths="notes/a.md",
            helpful=True,
            retrieval_id="20260709000000",
        )
    )


def test_feedback_fs_only_allows_writes(tmp_path: Any) -> None:
    resp = _feedback(tmp_path, "fs_only", ConnectionState.DISCONNECTED)
    assert "error" not in resp
    assert resp["updated"][0]["path"] == "notes/a.md"
    assert (tmp_path / "_meta" / "utility-scores.json").is_file()
    log_lines = (tmp_path / "_meta" / "feedback-log.jsonl").read_text().splitlines()
    assert json.loads(log_lines[-1])["event"] == "feedback"


def test_feedback_auto_disconnected_defers(tmp_path: Any) -> None:
    resp = _feedback(tmp_path, "auto", ConnectionState.DISCONNECTED)
    assert resp["error"] == "FEEDBACK_DEFERRED"
    assert not (tmp_path / "_meta" / "utility-scores.json").exists()
    assert not (tmp_path / "_meta" / "feedback-log.jsonl").exists()


def test_feedback_auto_connected_still_allows(tmp_path: Any) -> None:
    resp = _feedback(tmp_path, "auto", ConnectionState.CONNECTED)
    assert "error" not in resp
    assert resp["updated"][0]["newUtility"] > 0.5


# ---------------------------------------------------------------------------
# hive_retrieve log_retrieval gate
# ---------------------------------------------------------------------------

_MANIFEST = {
    "version": "2.0",
    "generated": "2026-07-09T00:00:00",
    "hive_path": "/tmp/vault",
    "note_count": 1,
    "stats": {},
    "notes": [
        {"path": "git-guide.md", "title": "Git rebase guide", "basename": "git-guide",
         "summary": "how to rebase branches", "updated": "2026-07-01", "inboundCount": 2},
    ],
}


def _retrieve(hive_path: Any, mode: str, state: ConnectionState) -> dict[str, Any]:
    meta = hive_path / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "hive-manifest.json").write_text(json.dumps(_MANIFEST), encoding="utf-8")
    return json.loads(
        build_retrieve_response(
            ManifestCache(hive_path),
            UtilityCache(hive_path),
            _settings(hive_path, mode),
            monitor=_monitor(state),  # type: ignore[arg-type]
            embedding_store=None,
            query="git",
            max_results=5,
        )
    )


def test_retrieval_logging_fs_only(tmp_path: Any) -> None:
    resp = _retrieve(tmp_path, "fs_only", ConnectionState.DISCONNECTED)
    assert resp["count"] == 1
    log_lines = (tmp_path / "_meta" / "feedback-log.jsonl").read_text().splitlines()
    event = json.loads(log_lines[-1])
    assert event["event"] == "retrieval"
    assert event["retrievalId"] == resp["retrievalId"]
    assert event["surfacedPaths"] == ["git-guide.md"]


def test_retrieval_logging_auto_disconnected_defers(tmp_path: Any) -> None:
    resp = _retrieve(tmp_path, "auto", ConnectionState.DISCONNECTED)
    assert resp["count"] == 1
    assert not (tmp_path / "_meta" / "feedback-log.jsonl").exists()
