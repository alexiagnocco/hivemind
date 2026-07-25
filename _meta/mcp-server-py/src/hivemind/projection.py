"""Response projection tiers — cumulative ``minimal ⊂ standard ⊂ full``.

Tools accept a ``detail`` parameter and project each result item down to the
requested tier before serializing. Tiers are key whitelists over the full
envelope, so every tier is a strict subset of the next: ``minimal`` carries
identity + rank (~30 tokens/item), ``standard`` adds skim context
(summary/updated/tags/utility), ``full`` is the unprojected envelope.

The deprecated ``slim`` boolean maps onto tiers via ``resolve_detail`` so
existing callers keep working.
"""

from __future__ import annotations

import json
from typing import Any

DETAIL_TIERS = ("minimal", "standard", "full")

# Identity + rank. "anchor" carries the heading target on chunk-level hits.
_MINIMAL_KEYS: tuple[str, ...] = ("path", "title", "score", "anchor")
# "section" and "excerpt" exist only on chunk-level hits; whitelist
# intersection means note-level items are unaffected by their presence here.
_STANDARD_KEYS: tuple[str, ...] = (
    *_MINIMAL_KEYS,
    "summary",
    "section",
    "excerpt",
    "updated",
    "tags",
    "utility",
    "status",
    "domain",
    "type",
)

_TIER_KEYS: dict[str, tuple[str, ...]] = {
    "minimal": _MINIMAL_KEYS,
    "standard": _STANDARD_KEYS,
}


def resolve_detail(detail: str, *, slim: bool | None = None, default: str = "standard") -> str:
    """Resolve a detail tier name.

    An explicit valid ``detail`` wins. Empty/unknown values fall back to the
    deprecated ``slim`` alias (True → ``default``, False → ``full``) when
    given, else to ``default``.
    """
    tier = detail.strip().lower()
    if tier in DETAIL_TIERS:
        return tier
    if slim is not None and not slim:
        return "full"
    return default


def project_item(item: dict[str, Any], detail: str) -> dict[str, Any]:
    """Project one result dict down to a tier. ``full`` returns it unchanged.

    Whitelist intersection: keys absent from the item are skipped, so the
    same tiers apply to retrieve candidates, search notes, and REST hits.
    """
    keys = _TIER_KEYS.get(detail)
    if keys is None:
        return item
    return {k: item[k] for k in keys if k in item}


def project_items(items: list[dict[str, Any]], detail: str) -> list[dict[str, Any]]:
    if detail == "full":
        return items
    return [project_item(i, detail) for i in items]


def to_json(payload: Any, *, compact: bool) -> str:
    """Serialize a tool response. Compact separators in the lean profile."""
    if compact:
        return json.dumps(payload, separators=(",", ":"))
    return json.dumps(payload, indent=2)
