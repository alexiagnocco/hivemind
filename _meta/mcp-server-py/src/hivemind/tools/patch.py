"""hive_patch tool — surgical heading/block/frontmatter edits. REST-only."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from hivemind.backend.dispatcher import RestUnavailableError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient

_VALID_TARGET_TYPES = frozenset({"heading", "block", "frontmatter"})
_VALID_OPERATIONS = frozenset({"append", "prepend", "replace"})


async def build_patch_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    path: str,
    target_type: str,
    target: str,
    content: str,
    operation: str = "append",
    target_delimiter: str = "::",
    create_if_missing: bool = False,
    apply_if_content_preexists: str = "",
) -> str:
    try:
        dispatcher.require_rest("hive_patch")
    except RestUnavailableError as exc:
        return str(exc)

    if target_type not in _VALID_TARGET_TYPES:
        valid = ", ".join(sorted(_VALID_TARGET_TYPES))
        return json.dumps(
            {"error": f"Invalid target_type '{target_type}'. Must be: {valid}"}
        )
    if operation not in _VALID_OPERATIONS:
        valid = ", ".join(sorted(_VALID_OPERATIONS))
        return json.dumps(
            {"error": f"Invalid operation '{operation}'. Must be: {valid}"}
        )

    try:
        resp = await client.patch_note(
            path,
            content,
            target_type=target_type,
            target=target,
            target_delimiter=target_delimiter,
            operation=operation,
            create_if_missing=create_if_missing,
            apply_if_content_preexists=apply_if_content_preexists or None,
        )
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "error": f"HTTP {exc.response.status_code}",
            "path": path,
            "target": target,
        }, indent=2)

    return json.dumps({
        "success": True,
        "path": path,
        "target": target,
        "operation": operation,
        "http_status": resp.status_code,
    }, indent=2)
