"""Projection tiers — cumulative superset property and per-tier size ceilings."""

from __future__ import annotations

import json
from typing import Any

from hivemind.projection import (
    DETAIL_TIERS,
    project_item,
    project_items,
    resolve_detail,
    to_json,
)

# Representative full-envelope hive_retrieve candidate.
_FULL_ITEM: dict[str, Any] = {
    "path": "30-resources/backend/auth-token-expiry-bug.md",
    "title": "Auth token expiry bug",
    "baseScore": 21,
    "utility": 0.5,
    "matchScore": 4,
    "freshnessScore": 5,
    "connectivityScore": 3,
    "updated": "2026-07-01",
    "status": "active",
    "inboundLinks": 3,
    "isArchived": False,
    "domain": "work",
    "tags": ["backend", "testing"],
    "summary": "Root cause and fix for the intermittent auth token expiry bug.",
    "denseScore": 0.4321,
    "mode": "hybrid",
    "score": 1.2345,
}


def test_tiers_are_cumulative_supersets() -> None:
    minimal = project_item(_FULL_ITEM, "minimal")
    standard = project_item(_FULL_ITEM, "standard")
    full = project_item(_FULL_ITEM, "full")
    assert set(minimal) < set(standard) < set(full)
    # Cumulative: lower tiers never rewrite values, only drop keys.
    assert all(standard[k] == v for k, v in minimal.items())
    assert all(full[k] == v for k, v in standard.items())


def test_minimal_carries_identity_and_rank() -> None:
    minimal = project_item(_FULL_ITEM, "minimal")
    assert minimal == {
        "path": _FULL_ITEM["path"],
        "title": _FULL_ITEM["title"],
        "score": _FULL_ITEM["score"],
    }


def test_per_tier_size_ceilings() -> None:
    sizes = {t: len(json.dumps(project_item(_FULL_ITEM, t))) for t in DETAIL_TIERS}
    assert sizes["minimal"] <= 150
    assert sizes["standard"] <= 450
    assert sizes["minimal"] < sizes["standard"] < sizes["full"]


def test_project_item_skips_keys_absent_from_source() -> None:
    # Search notes have no score; REST hits have no title. Same tiers apply.
    projected = project_item({"path": "a.md", "matches": []}, "minimal")
    assert projected == {"path": "a.md"}


def test_project_items_full_is_identity() -> None:
    items = [_FULL_ITEM]
    assert project_items(items, "full") is items


def test_resolve_detail_explicit_tier_wins_over_slim() -> None:
    assert resolve_detail("full", slim=True, default="minimal") == "full"
    assert resolve_detail("Minimal ", slim=False, default="standard") == "minimal"


def test_resolve_detail_slim_alias_and_defaults() -> None:
    assert resolve_detail("", slim=True, default="minimal") == "minimal"
    assert resolve_detail("", slim=False, default="minimal") == "full"
    assert resolve_detail("", default="standard") == "standard"
    assert resolve_detail("bogus", default="standard") == "standard"


def test_to_json_compact_strips_whitespace() -> None:
    payload = {"a": [1, 2], "b": "x"}
    compact = to_json(payload, compact=True)
    pretty = to_json(payload, compact=False)
    assert " " not in compact and "\n" not in compact
    assert json.loads(compact) == json.loads(pretty) == payload
    assert len(compact) < len(pretty)
