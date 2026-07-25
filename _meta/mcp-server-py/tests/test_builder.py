"""Tests for the manifest builder's vault walk.

Locks in two boundaries: tool caches (.pytest_cache) are never indexed,
while the .github Copilot surface IS indexed — is_system_note handles its
metrics classification, not walk exclusion (see test_paths.py).
"""

from __future__ import annotations

from pathlib import Path

from hivemind.manifest.builder import build_manifest


def _write(root: Path, rel: str, text: str = "# Note\n\nbody\n") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestManifestWalk:
    def test_pytest_cache_is_not_indexed(self, tmp_path: Path) -> None:
        _write(tmp_path, "30-resources/backend/real-note.md")
        _write(tmp_path, "_meta/mcp-server-py/.pytest_cache/README.md")
        manifest = build_manifest(tmp_path)
        paths = [n["path"] for n in manifest["notes"]]
        assert paths == ["30-resources/backend/real-note.md"]

    def test_github_surface_is_indexed(self, tmp_path: Path) -> None:
        # The Copilot surface must stay in the index (retrievable via
        # hive_retrieve/hive_context); it is classified as system for
        # metrics by is_system_note, not excluded from the walk.
        _write(tmp_path, ".github/agents/hivemind.agent.md")
        _write(tmp_path, ".github/prompts/boot.prompt.md")
        _write(tmp_path, "README.md")
        manifest = build_manifest(tmp_path)
        paths = sorted(n["path"] for n in manifest["notes"])
        assert paths == [
            ".github/agents/hivemind.agent.md",
            ".github/prompts/boot.prompt.md",
            "README.md",
        ]

    def test_repo_surface_not_counted_in_orphan_stats(self, tmp_path: Path) -> None:
        _write(tmp_path, ".github/copilot-instructions.md")
        _write(tmp_path, "README.md")
        _write(tmp_path, "30-resources/backend/genuine-orphan.md")
        manifest = build_manifest(tmp_path)
        assert manifest["stats"]["orphanNotes"] == 1
