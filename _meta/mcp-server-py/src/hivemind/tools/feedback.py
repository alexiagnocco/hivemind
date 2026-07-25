"""hive_feedback tool — record helpful/not-helpful feedback, update utility via EMA."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hivemind.scoring.memrl import memrl_writes_allowed, update_feedback
from hivemind.scoring.relevance import ALPHA

if TYPE_CHECKING:
    from hivemind.config import Settings
    from hivemind.rest.connection import ConnectionMonitor
    from hivemind.state.utility import UtilityCache


def build_feedback_response(
    utility_cache: UtilityCache,
    settings: Settings,
    *,
    monitor: ConnectionMonitor,
    paths: str,
    helpful: bool,
    retrieval_id: str = "",
) -> str:
    if not memrl_writes_allowed(settings, monitor):
        return json.dumps({
            "error": "FEEDBACK_DEFERRED",
            "reason": "MemRL writes deferred — REST not CONNECTED and fallback"
            " mode is not fs_only (stale snapshot risk)",
            "state": str(monitor.current_state),
        }, indent=2)

    path_list = [p.strip() for p in paths.split(",") if p.strip()]
    updated = update_feedback(
        settings.hive_path,
        utility_cache,
        paths=path_list,
        helpful=helpful,
        retrieval_id=retrieval_id,
    )

    return json.dumps({
        "updated": updated,
        "reward": 1.0 if helpful else 0.0,
        "alpha": ALPHA,
        "message": f"Updated {len(updated)} note(s) utility scores"
        f" ({'+'if helpful else '-'})",
    }, indent=2)
