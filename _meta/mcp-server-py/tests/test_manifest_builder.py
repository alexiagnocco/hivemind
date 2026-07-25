"""Tests for the native manifest builder (hivemind.manifest.builder)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hivemind.manifest.builder import build_manifest

if TYPE_CHECKING:
    from pathlib import Path

NOTE = """---
created: 2026-07-01
updated: 2026-07-01
tags: [ai]
status: active
type: note
domain: work
---

# A Real Note

Body text linking [[another-note]].
"""


def _write(path: Path, text: str = NOTE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_dot_directories_are_excluded(tmp_path: Path) -> None:
    """Markdown inside any dot-directory must never enter the index.

    Tool caches drop stray markdown next to real notes — .venv site-packages,
    .pytest_cache/README.md — and an index polluted with them produces phantom
    orphans and garbage retrieval hits on a freshly provisioned clone.
    """
    _write(tmp_path / "30-resources" / "real-note.md")
    _write(tmp_path / ".pytest_cache" / "README.md")
    _write(tmp_path / ".venv" / "lib" / "site-packages" / "pkg" / "README.md")
    _write(tmp_path / "30-resources" / ".hidden-dir" / "nested.md")

    manifest = build_manifest(tmp_path)
    paths = [n["path"] for n in manifest["notes"]]

    assert paths == ["30-resources/real-note.md"]


def test_enumerated_exclude_dirs_still_apply(tmp_path: Path) -> None:
    _write(tmp_path / "10-projects" / "keep.md")
    _write(tmp_path / "_templates" / "note-template.md")
    _write(tmp_path / "node_modules" / "pkg" / "README.md")

    manifest = build_manifest(tmp_path)
    paths = [n["path"] for n in manifest["notes"]]

    assert paths == ["10-projects/keep.md"]
