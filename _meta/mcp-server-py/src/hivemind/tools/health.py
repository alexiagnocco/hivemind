"""hive_health tool — knowledge health metrics."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hivemind.scoring.health import compute_health
from hivemind.state.feedback import read_jsonl

if TYPE_CHECKING:
    from hivemind.config import Settings
    from hivemind.state.manifest_cache import ManifestCache
    from hivemind.state.utility import UtilityCache


def build_health_response(
    cache: ManifestCache,
    utility_cache: UtilityCache,
    settings: Settings,
    *,
    window_days: int = 7,
    stale_threshold_days: int = 30,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    feedback_log_path = settings.hive_path / "_meta" / "feedback-log.jsonl"
    all_events = read_jsonl(feedback_log_path)
    feedback_events = [e for e in all_events if e.get("event") == "retrieval"]

    result = compute_health(
        manifest.notes,
        feedback_events,
        utility_cache.load(),
        window_days=window_days,
        stale_threshold_days=stale_threshold_days,
    )

    return json.dumps(result, indent=2)
