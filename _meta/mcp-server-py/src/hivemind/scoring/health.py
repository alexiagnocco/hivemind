"""Health metrics computation: K, I(t), delta, sigma, rho, phi, escape velocity, dK/dt.

Verbatim port of the hive_health logic in index.ts lines 303-388.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from hivemind.fs.paths import is_system_note
from hivemind.scoring.relevance import round_val

if TYPE_CHECKING:
    from hivemind.model.note import Note
    from hivemind.state.utility import UtilityScores


def compute_health(
    notes: list[Note],
    feedback_events: list[dict[str, Any]],
    utility_scores: UtilityScores,
    *,
    window_days: int = 7,
    stale_threshold_days: int = 30,
) -> dict[str, Any]:
    """Compute the full health metrics dictionary."""
    now = datetime.now(UTC)
    window_cutoff = (now - timedelta(days=window_days)).strftime("%Y-%m-%d")
    stale_cutoff = (now - timedelta(days=stale_threshold_days)).strftime("%Y-%m-%d")

    active = [n for n in notes if not n.path.startswith("40-archive")]
    archived = [n for n in notes if n.path.startswith("40-archive")]

    k = len(active)
    it = len([n for n in active if (n.created or "") >= window_cutoff])
    stale_count = len([n for n in active if (n.updated or "") < stale_cutoff])
    delta = round_val(stale_count / k, 3) if k > 0 else 0.0

    content = [n for n in active if not is_system_note(n.path)]
    content_linked = len([n for n in content if n.inboundCount > 0])
    content_orphans = len(content) - content_linked
    total_orphans = len([n for n in active if n.inboundCount == 0])

    sigma = round_val(content_linked / len(content), 3) if content else 0.0
    multi_update = len([n for n in content if (n.updated or "") != (n.created or "")])
    rho = round_val(multi_update / content_linked, 3) if content_linked > 0 else 0.0
    phi = round_val(content_orphans / len(content), 3) if content else 0.0
    sigma_rho = round_val(sigma * rho, 4)
    delta_threshold = round_val(delta / 100, 4)
    escape_velocity = sigma_rho > delta_threshold
    health = round_val(sigma_rho - delta_threshold, 4)
    status = "COMPOUNDING" if escape_velocity else "DECAYING"
    decay_term = round_val(delta * k, 1)
    compound_term = round_val(sigma * rho * k, 1)
    dk_dt = round_val(it - decay_term + compound_term, 1)

    memrl = _compute_memrl(
        active, feedback_events, utility_scores, delta_threshold
    )

    summary = (
        f"K={k} ({len(content)} content) | I(t)={it}/{window_days}d | "
        f"delta={delta} | sigma={sigma} | rho={rho} | "
        f"sigma*rho={sigma_rho} vs {delta_threshold} | {status} | "
        f"dK/dt={dk_dt} | orphans={content_orphans} actionable / {total_orphans} total"
    )
    if memrl:
        summary += f" | MemRL: true_sigma={memrl['true_sigma']} true_rho={memrl['true_rho']}"
    else:
        summary += " | MemRL: insufficient data (<10 events)"

    return {
        "status": status,
        "K": k,
        "K_content": len(content),
        "K_system": k - len(content),
        "K_archived": len(archived),
        "It": it,
        "It_window": f"{window_days}d",
        "delta": delta,
        "delta_stale_count": stale_count,
        "delta_threshold": f"{stale_threshold_days}d",
        "sigma_proxy": sigma,
        "sigma_linked": content_linked,
        "sigma_content_notes": len(content),
        "sigma_orphans_actionable": content_orphans,
        "sigma_orphans_total": total_orphans,
        "rho_proxy": rho,
        "rho_multi_update": multi_update,
        "phi": phi,
        "sigma_x_rho_proxy": sigma_rho,
        "delta_over_100": delta_threshold,
        "escape_velocity": escape_velocity,
        "health": health,
        "dKdt": dk_dt,
        "memrl": memrl,
        "summary": summary,
    }


def compute_sigma_rho(
    notes: list[Note],
    feedback_events: list[dict[str, Any]],
    utility_scores: UtilityScores,
) -> dict[str, Any]:
    """Shared sigma/rho computation used by both hive_health and hive_sigma_rho."""
    all_surfaced: set[str] = set()
    for evt in feedback_events:
        for p in evt.get("surfacedPaths", []):
            all_surfaced.add(str(p))

    active = [n for n in notes if not n.path.startswith("40-archive")]
    retrievable = [
        n for n in active
        if not n.path.startswith("_templates") and not is_system_note(n.path)
    ]
    retrievable_count = len(retrievable)
    true_sigma = (
        round_val(len(all_surfaced) / retrievable_count, 3)
        if retrievable_count > 0
        else 0.0
    )

    cited = {
        path for path, entry in utility_scores.items()
        if entry.citations > 0
    }
    surfaced_and_cited = len([p for p in all_surfaced if p in cited])
    true_rho = (
        round_val(surfaced_and_cited / len(all_surfaced), 3)
        if all_surfaced
        else 0.0
    )
    true_sr = round_val(true_sigma * true_rho, 4)

    return {
        "true_sigma": true_sigma,
        "true_rho": true_rho,
        "true_sigma_x_rho": true_sr,
        "surfaced_unique": len(all_surfaced),
        "total_retrievable": retrievable_count,
        "cited_count": len(cited),
        "feedback_events": len(feedback_events),
        "scored_notes": len(utility_scores),
    }


def _compute_memrl(
    active: list[Note],
    feedback_events: list[dict[str, Any]],
    utility_scores: UtilityScores,
    delta_threshold: float,
) -> dict[str, Any] | None:
    if len(feedback_events) < 10:
        return None

    sr = compute_sigma_rho(active, feedback_events, utility_scores)
    return {
        "true_sigma": sr["true_sigma"],
        "true_rho": sr["true_rho"],
        "true_sigma_x_rho": sr["true_sigma_x_rho"],
        "true_escape_velocity": sr["true_sigma_x_rho"] > delta_threshold,
        "feedback_events": sr["feedback_events"],
        "scored_notes": sr["scored_notes"],
    }
