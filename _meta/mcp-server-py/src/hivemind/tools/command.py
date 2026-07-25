"""hive_command tool — list/run Obsidian commands. REST-only."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from hivemind.backend.dispatcher import RestUnavailableError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient


async def build_command_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    action: str = "list",
    command_id: str = "",
) -> str:
    try:
        dispatcher.require_rest("hive_command")
    except RestUnavailableError as exc:
        return str(exc)

    try:
        if action == "list":
            commands = await client.list_commands()
            return json.dumps({
                "commands": commands,
                "count": len(commands),
            }, indent=2)

        if action == "run":
            if not command_id.strip():
                return json.dumps({"error": "command_id is required for action='run'"})
            resp = await client.run_command(command_id)
            return json.dumps({
                "success": True,
                "command_id": command_id,
                "http_status": resp.status_code,
            }, indent=2)

        return json.dumps({"error": f"Invalid action '{action}'. Must be 'list' or 'run'."})
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "error": f"HTTP {exc.response.status_code}",
            "action": action,
        }, indent=2)
