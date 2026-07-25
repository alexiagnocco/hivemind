from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from hivemind.backend.dispatcher import RestUnavailableError
from hivemind.rest.errors import ObsidianRestError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient


async def build_tags_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
) -> str:
    try:
        dispatcher.require_rest("hive_tags")
    except RestUnavailableError as exc:
        return str(exc)

    try:
        raw: dict[str, Any] = await client.list_tags()
    except (httpx.HTTPStatusError, ObsidianRestError) as exc:
        return json.dumps({"error": str(exc), "tags": []}, indent=2)

    tags_list = raw.get("tags", [])

    return json.dumps(
        {"tags": tags_list, "total_unique": len(tags_list)},
        indent=2,
    )
