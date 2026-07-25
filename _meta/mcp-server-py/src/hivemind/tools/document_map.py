from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from hivemind.backend.dispatcher import RestUnavailableError
from hivemind.rest.errors import ObsidianRestError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient


async def build_document_map_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    path: str,
) -> str:
    try:
        dispatcher.require_rest("hive_document_map")
    except RestUnavailableError as exc:
        return str(exc)

    try:
        result = await client.get_document_map(path)
    except httpx.HTTPStatusError as exc:
        return json.dumps(
            {"error": f"HTTP {exc.response.status_code}", "path": path},
            indent=2,
        )
    except ObsidianRestError as exc:
        return json.dumps({"error": str(exc), "path": path}, indent=2)

    return json.dumps(result, indent=2)
