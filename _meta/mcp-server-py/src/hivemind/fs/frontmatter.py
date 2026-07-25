"""Minimal YAML frontmatter parser — port of manifest-builder.ts parseFrontmatter.

Intentional parity deviation: this parser handles multiline YAML lists
(``tags:\\n  - ai\\n  - meta``) which the TS v3 parser skips (lines without
colons are discarded).  The Phase 5 parity test must account for tag
differences on notes that use multiline format.
"""

from __future__ import annotations

import re
from typing import Any

_ARRAY_INLINE_RE = re.compile(r"^\[(.+)]$")


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()

    fm: dict[str, Any] = {}
    pending_list_key: str | None = None
    pending_list: list[str] = []

    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if pending_list_key is not None and line.startswith("  - "):
            item = stripped[2:] if stripped.startswith("- ") else stripped
            pending_list.append(item.strip().strip("\"'"))
            continue
        if pending_list_key is not None:
            fm[pending_list_key] = pending_list
            pending_list_key = None
            pending_list = []

        colon_idx = stripped.find(":")
        if colon_idx == -1:
            continue

        key = stripped[:colon_idx].strip()
        value_str = stripped[colon_idx + 1 :].strip()

        if not value_str:
            pending_list_key = key
            pending_list = []
            continue

        value: Any
        m = _ARRAY_INLINE_RE.match(value_str)
        if m:
            value = [s.strip().strip("\"'") for s in m.group(1).split(",") if s.strip()]
        elif (
            (value_str.startswith('"') and value_str.endswith('"'))
            or (value_str.startswith("'") and value_str.endswith("'"))
        ):
            value = value_str[1:-1]
        elif value_str == "true":
            value = True
        elif value_str == "false":
            value = False
        else:
            value = value_str

        fm[key] = value

    if pending_list_key is not None:
        fm[pending_list_key] = pending_list

    return fm
