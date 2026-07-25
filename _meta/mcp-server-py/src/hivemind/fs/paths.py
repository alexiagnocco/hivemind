from __future__ import annotations

import re

_META_TOPLEVEL_RE = re.compile(r"^_meta/[^/]+\.(md|json|jsonl)$")


def is_system_note(path: str) -> bool:
    """Ported from helpers.ts isSystemNote (lines 300-319), extended for
    repo-surface files: .github/** and the root repo docs stay indexed and
    retrievable but never count as content notes or orphans in health
    metrics, session checks, or pruning.
    """
    if path.startswith("40-archive/"):
        return True
    if path.startswith(".github/"):
        return True
    if path.startswith("_templates/"):
        return True
    if path.startswith("_meta/inbox/"):
        return True
    if path.startswith("_meta/mcp-server") and "/" in path[len("_meta/mcp-server"):]:
        return True
    if path.startswith("_meta/scripts/"):
        return True
    if path.startswith("_meta/_archive/"):
        return True
    if _META_TOPLEVEL_RE.match(path):
        return True
    if "/references/" in path:
        return True
    if path.endswith("/SKILL.md") or path.endswith("\\SKILL.md"):
        return True
    if path.startswith("memory/feedback_") or path.startswith("memory/reference_"):
        return True
    if path.endswith("/_README.md") or path == "_README.md":
        return True
    return path in (
        "CLAUDE.md",
        "EXAMPLES.md",
        "README.md",
        "CREDITS.md",
        "STRUCTURE.md",
        "LICENSE.md",
        "memory/MEMORY.md",
    )
