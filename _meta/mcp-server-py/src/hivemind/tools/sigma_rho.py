"""hive_sigma_rho tool — compute true sigma and rho from MemRL feedback data."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hivemind.scoring.health import compute_sigma_rho
from hivemind.scoring.relevance import round_val
from hivemind.state.feedback import read_jsonl

if TYPE_CHECKING:
    from hivemind.config import Settings
    from hivemind.state.manifest_cache import ManifestCache
    from hivemind.state.utility import UtilityCache


def build_sigma_rho_response(
    cache: ManifestCache,
    utility_cache: UtilityCache,
    settings: Settings,
) -> str:
    scores = utility_cache.load()
    feedback_log_path = settings.hive_path / "_meta" / "feedback-log.jsonl"
    events = [e for e in read_jsonl(feedback_log_path) if e.get("event") == "retrieval"]

    manifest = cache.load()
    sr = compute_sigma_rho(manifest.notes, events, scores)

    utilities = [entry.utility for entry in scores.values()]
    avg_utility = (
        round_val(sum(utilities) / len(utilities), 3) if utilities else 0.5
    )

    sorted_scores = sorted(
        scores.items(), key=lambda kv: kv[1].utility, reverse=True
    )
    top_5 = [
        {
            "path": p,
            "utility": e.utility,
            "citations": e.citations,
            "retrievals": e.retrievals,
        }
        for p, e in sorted_scores[:5]
    ]
    bottom_5 = (
        [
            {
                "path": p,
                "utility": e.utility,
                "citations": e.citations,
                "retrievals": e.retrievals,
            }
            for p, e in sorted_scores[-5:]
        ]
        if len(sorted_scores) >= 5
        else []
    )

    return json.dumps({
        "true_sigma": sr["true_sigma"],
        "true_rho": sr["true_rho"],
        "true_sigma_x_rho": sr["true_sigma_x_rho"],
        "sufficient_data": len(events) >= 10,
        "data_quality": (
            f"{len(events)} retrieval events, {len(scores)} scored notes"
        ),
        "surfaced_unique": sr["surfaced_unique"],
        "total_retrievable": sr["total_retrievable"],
        "cited_count": sr["cited_count"],
        "avg_utility": avg_utility,
        "high_utility_notes": len([u for u in utilities if u > 0.7]),
        "low_utility_notes": len([u for u in utilities if u < 0.3]),
        "top_5": top_5,
        "bottom_5": bottom_5,
        "note": "Proxy metrics used when sufficient_data=false"
        if len(events) < 10
        else "True metrics active",
    }, indent=2)
