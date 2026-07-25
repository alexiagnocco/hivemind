"""hive_active tool — read/append/replace the currently-open editor note. REST-only."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from hivemind.backend.dispatcher import RestUnavailableError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient

_VALID_ACTIONS = frozenset({"read", "append", "replace"})


async def build_active_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    action: str = "read",
    content: str = "",
) -> str:
    try:
        dispatcher.require_rest("hive_active")
    except RestUnavailableError as exc:
        return str(exc)

    if action not in _VALID_ACTIONS:
        valid = ", ".join(sorted(_VALID_ACTIONS))
        return json.dumps({"error": f"Invalid action '{action}'. Must be: {valid}"})

    try:
        if action == "read":
            return await _read_active(client)
        if action == "append":
            resp = await client.post_active(content)
            return json.dumps({
                "success": True,
                "http_status": resp.status_code,
            }, indent=2)
        # replace
        resp = await client.put_active(content)
        return json.dumps({
            "success": True,
            "http_status": resp.status_code,
        }, indent=2)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return json.dumps({
                "error": "No note is currently open in Obsidian",
                "success": False,
            }, indent=2)
        raise


async def _read_active(client: ObsidianRestClient) -> str:
    result: dict[str, Any] | str = await client.get_active(as_json=True)
    if isinstance(result, dict):
        return json.dumps({
            "path": result.get("path", ""),
            "content": result.get("content", ""),
            "frontmatter": result.get("frontmatter", {}),
            "tags": result.get("tags", []),
            "success": True,
        }, indent=2)
    return json.dumps({"content": result, "success": True}, indent=2)
