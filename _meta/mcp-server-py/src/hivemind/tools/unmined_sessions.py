"""hive_unmined_sessions tool — find sessions not yet mined for knowledge extraction."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hivemind.state.sessions import read_processed_session_ids, read_session_log

if TYPE_CHECKING:
    from hivemind.config import Settings


def build_unmined_sessions_response(
    settings: Settings,
    *,
    slim: bool = True,
) -> str:
    sessions = read_session_log(settings.hive_path)
    processed_ids = read_processed_session_ids(settings.hive_path)

    unmined = [
        s for s in sessions
        if s.get("sessionId")
        and s["sessionId"] not in processed_ids
        and s.get("mineRecommended", True)
    ]

    if slim:
        output = [
            {
                "sessionId": s.get("sessionId"),
                "project": s.get("project", ""),
                "date": s.get("date", s.get("timestamp", "")),
                "sizeKB": s.get("sizeKB", 0),
                "userMessages": s.get("userMessages", 0),
                "mineRecommended": s.get("mineRecommended", False),
            }
            for s in unmined
        ]
    else:
        output = unmined

    return json.dumps({
        "unmined": output,
        "unminedCount": len(unmined),
        "totalSessions": len(sessions),
        "minedSessions": len(processed_ids),
    }, indent=2)
