"""hive_open tool — bring a note into focus in Obsidian UI. REST-only."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from hivemind.backend.dispatcher import RestUnavailableError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient


async def build_open_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    path: str,
    new_leaf: bool = True,
) -> str:
    try:
        dispatcher.require_rest("hive_open")
    except RestUnavailableError as exc:
        return str(exc)

    try:
        await client.open_in_ui(path, new_leaf=new_leaf)
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "error": f"HTTP {exc.response.status_code}",
            "path": path,
        }, indent=2)
    return json.dumps({"success": True, "path": path}, indent=2)
