"""hive_checkpoint tool — mid-session incremental project memory update.

REST path: two PATCHes — (1) heading append under `## Session Checkpoints`
with a unique `### Checkpoint <ISO>` subheading, (2) frontmatter PATCH on
`updated` field. ISO-8601-with-seconds-and-Z guarantees heading uniqueness.

FS fallback: file append + regex frontmatter rewrite. Uses the same ISO
heading format as REST so files are structurally identical regardless of
write path. This is an intentional upgrade from the TS v3 format
(`### Checkpoint YYYY-MM-DD HH:MM`) which could collide.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.config import Settings
    from hivemind.rest.client import ObsidianRestClient

logger = logging.getLogger(__name__)


def _sanitize_field(value: str) -> str:
    """Strip characters that could corrupt markdown structure."""
    return value.replace("\r", "").replace("\n", " ").strip()


async def build_checkpoint_response(
    settings: Settings,
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    project: str,
    summary: str,
    decisions: str = "",
    blockers: str = "",
) -> str:
    mem_rel = f"memory/projects/{project}.md"
    mem_path = (settings.hive_path / mem_rel).resolve()
    if not mem_path.is_relative_to(settings.hive_path.resolve()):
        return json.dumps({"success": False, "error": "Invalid project slug"})

    if not mem_path.exists():
        return json.dumps({
            "success": False,
            "error": f"Project memory not found: {mem_rel}",
        })

    summary = _sanitize_field(summary)
    decisions = _sanitize_field(decisions)
    blockers = _sanitize_field(blockers)

    now = datetime.now(UTC)
    iso_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    display_ts = now.strftime("%Y-%m-%d %H:%M")
    today = now.strftime("%Y-%m-%d")

    entry_body = f"### Checkpoint {iso_ts}\n\n- {summary}\n"
    if decisions:
        entry_body += f"- **Decisions:** {decisions}\n"
    if blockers:
        entry_body += f"- **Blockers:** {blockers}\n"

    from hivemind.backend.dispatcher import Backend

    backend = dispatcher.pick(prefer=Backend.REST)
    mode_used = "rest" if backend == Backend.REST else "fs"

    if backend == Backend.REST:
        try:
            await _checkpoint_rest(client, mem_rel, entry_body, today)
        except Exception as exc:
            logger.warning(
                "REST checkpoint failed for %s, falling back to FS: %s",
                project,
                exc,
            )
            _checkpoint_fs(mem_path, entry_body, today)
            mode_used = "fs_fallback"
    else:
        _checkpoint_fs(mem_path, entry_body, today)

    return json.dumps({
        "success": True,
        "project": project,
        "path": str(mem_path),
        "timestamp": display_ts,
        "mode_used": mode_used,
        "message": f"Checkpoint appended to {project} project memory",
    }, indent=2)


async def _checkpoint_rest(
    client: ObsidianRestClient,
    path: str,
    entry_body: str,
    today: str,
) -> None:
    """Two PATCHes: heading append + frontmatter update.

    If the heading PATCH succeeds but the frontmatter PATCH fails, the
    checkpoint content is already written. The frontmatter update is
    retried opportunistically on the next checkpoint (idempotent — same
    date is a no-op). We do NOT fall back to FS on frontmatter-only
    failure to avoid duplicating the entry body.
    """
    await client.patch_note(
        path,
        entry_body,
        target_type="heading",
        target="Session Checkpoints",
        operation="append",
        create_if_missing=True,
    )

    try:
        await client.patch_note(
            path,
            f'"{today}"',
            target_type="frontmatter",
            target="updated",
            operation="replace",
            content_type="application/json",
            create_if_missing=True,
        )
    except Exception as exc:
        logger.warning(
            "Frontmatter PATCH failed for %s (entry already written): %s",
            path,
            exc,
        )


_UPDATED_RE = re.compile(r"^updated:\s*\d{4}-\d{2}-\d{2}", re.MULTILINE)


def _checkpoint_fs(
    mem_path: Path,
    entry_body: str,
    today: str,
) -> None:
    """FS fallback: append entry + regex frontmatter rewrite (atomic)."""
    content = mem_path.read_text(encoding="utf-8")
    content += f"\n{entry_body}"
    content = _UPDATED_RE.sub(f"updated: {today}", content)
    tmp = mem_path.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, mem_path)
