"""MemRL EMA update logic.

Handles utility score updates (EMA) and retrieval logging.
Write operations fire when REST is CONNECTED or the vault runs in fs_only
fallback mode (see ``memrl_writes_allowed``); otherwise they are deferred to
avoid recording feedback against stale manifest snapshots.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from hivemind.config import FallbackMode
from hivemind.rest.connection import ConnectionState
from hivemind.scoring.relevance import ALPHA, round_val
from hivemind.state.feedback import append_feedback_log

if TYPE_CHECKING:
    from pathlib import Path

    from hivemind.config import Settings
    from hivemind.rest.connection import ConnectionMonitor
    from hivemind.state.utility import UtilityCache


def memrl_writes_allowed(settings: Settings, monitor: ConnectionMonitor) -> bool:
    """Whether MemRL writes (feedback updates, retrieval logs) may proceed.

    Allowed when REST is CONNECTED, or in fs_only fallback mode — there the
    filesystem is the live source of truth, so stale-snapshot risk doesn't
    apply and FS-only users still get the MemRL learning loop.
    """
    if settings.obsidian_fallback_mode is FallbackMode.FS_ONLY:
        return True
    return monitor.current_state is ConnectionState.CONNECTED


def log_retrieval(
    hive_path: Path,
    utility_cache: UtilityCache,
    *,
    retrieval_id: str,
    query: str,
    project: str,
    domain: str,
    surfaced_paths: list[str],
) -> None:
    """Log a retrieval event and bump retrieval counts."""
    now = datetime.now(UTC).isoformat()

    append_feedback_log(hive_path, {
        "event": "retrieval",
        "retrievalId": retrieval_id,
        "timestamp": now,
        "query": query,
        "project": project,
        "domain": domain,
        "surfacedPaths": surfaced_paths,
        "surfacedCount": len(surfaced_paths),
    })

    scores = utility_cache.load()
    for path in surfaced_paths:
        entry = scores.get(path)
        if entry is None:
            from hivemind.state.utility import UtilityEntry as UE

            scores[path] = UE(utility=0.5, retrievals=1, citations=0, lastUpdated=now)
        else:
            entry.retrievals += 1
            entry.lastUpdated = now
    utility_cache.save(scores)


def update_feedback(
    hive_path: Path,
    utility_cache: UtilityCache,
    *,
    paths: list[str],
    helpful: bool,
    retrieval_id: str = "",
) -> list[dict[str, Any]]:
    """Apply EMA update for feedback. Returns list of {path, oldUtility, newUtility}."""
    now = datetime.now(UTC).isoformat()
    reward = 1.0 if helpful else 0.0
    scores = utility_cache.load()
    updated: list[dict[str, Any]] = []

    for path in paths:
        entry = scores.get(path)
        if entry is None:
            from hivemind.state.utility import UtilityEntry as UE

            entry = UE(utility=0.5, retrievals=0, citations=0, lastUpdated="")
            scores[path] = entry
        old_util = entry.utility
        entry.utility = round_val((1 - ALPHA) * old_util + ALPHA * reward, 4)
        if helpful:
            entry.citations += 1
        entry.lastUpdated = now
        updated.append({"path": path, "oldUtility": old_util, "newUtility": entry.utility})

    utility_cache.save(scores)

    append_feedback_log(hive_path, {
        "event": "feedback",
        "timestamp": now,
        "retrievalId": retrieval_id,
        "helpful": helpful,
        "paths": paths,
    })

    return updated
