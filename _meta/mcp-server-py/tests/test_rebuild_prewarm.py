"""hive_rebuild pre-warm + first-call chunk-index build (Phase 3.2 AC).

Boots the real FastMCP server in-process against a fixture vault (fs_only,
hashing embeddings, no Obsidian) and asserts that the first chunk-granularity
hive_retrieve call builds the chunk index, and that hive_rebuild pre-warms
it so the next chunk query reuses the cache byte-for-byte.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

_NOTES = {
    "30-resources/git/rebase-guide.md": (
        "---\ncreated: 2026-07-01\nupdated: 2026-07-08\ntags: [git]\n"
        "status: active\ntype: note\ndomain: work\n---\n"
        "# Git rebase guide\n\nHow to rebase feature branches cleanly.\n\n"
        "## Interactive rebase\nUse rebase -i to squash fixup commits before review.\n\n"
        "## Conflict handling\nResolve conflicts hunk by hunk, then continue the rebase.\n"
    ),
    "30-resources/backend/sql-patterns.md": (
        "---\ncreated: 2026-07-01\nupdated: 2026-07-05\ntags: [backend]\n"
        "status: active\ntype: note\ndomain: work\n---\n"
        "# SQL patterns\n\nQuery shapes, indexes, and joins.\n"
    ),
}


def _text_of(result: object) -> str:
    content = getattr(result, "content", None) or []
    return "".join(getattr(block, "text", "") for block in content)


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: Any) -> Path:
    monkeypatch.setenv("HIVE_PATH", str(tmp_path))
    monkeypatch.setenv("OBSIDIAN_FALLBACK_MODE", "fs_only")
    monkeypatch.setenv("OBSIDIAN_API_KEY", "")
    monkeypatch.setenv("HIVEMIND_EMBEDDINGS_BACKEND", "hashing")
    for rel, text in _NOTES.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    from hivemind.manifest.builder import build_and_write_manifest

    build_and_write_manifest(tmp_path)
    return tmp_path


async def test_first_chunk_call_builds_index(vault: Path) -> None:
    from fastmcp import Client

    from hivemind.server import mcp

    chunks_file = vault / "_meta" / "hive-chunks.json"
    assert not chunks_file.exists()
    async with Client(mcp) as client:
        resp = json.loads(
            _text_of(
                await client.call_tool(
                    "hive_retrieve", {"query": "rebase", "granularity": "chunk"}
                )
            )
        )
        assert resp["count"] >= 1
        assert resp["results"][0]["path"] == "30-resources/git/rebase-guide.md"
        # First call completed the lazy chunk-index build and persisted it.
        assert chunks_file.is_file()


async def test_hive_rebuild_prewarms_chunk_index(vault: Path) -> None:
    from fastmcp import Client

    from hivemind.server import mcp

    chunks_file = vault / "_meta" / "hive-chunks.json"
    async with Client(mcp) as client:
        text = _text_of(await client.call_tool("hive_rebuild", {}))
        assert "Chunk index warmed:" in text
        assert chunks_file.is_file()
        warmed = chunks_file.read_bytes()
        # The pre-warmed cache satisfies the next chunk query as-is: no
        # re-chunk, no re-embed, byte-identical cache after the call.
        resp = json.loads(
            _text_of(
                await client.call_tool(
                    "hive_retrieve", {"query": "rebase", "granularity": "chunk"}
                )
            )
        )
        assert resp["count"] >= 1
        assert chunks_file.read_bytes() == warmed
