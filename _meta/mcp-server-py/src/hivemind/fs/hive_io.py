from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def read_note(hive_path: Path, rel_path: str) -> str:
    full = (hive_path / rel_path).resolve()
    if not full.is_relative_to(hive_path.resolve()):
        msg = f"Path traversal blocked: {rel_path}"
        raise ValueError(msg)
    return full.read_text(encoding="utf-8")


def read_notes(hive_path: Path, paths: list[str]) -> str:
    parts: list[str] = []
    for rel_path in paths:
        try:
            content = read_note(hive_path, rel_path.strip())
            if len(paths) > 1:
                parts.append(f"=== {rel_path.strip()} ===\n{content}")
            else:
                parts.append(content)
        except Exception as exc:
            parts.append(f"ERROR: {exc}")
    return "\n\n".join(parts)
