"""hive_periodic tool — daily/weekly/monthly/quarterly/yearly CRUD. REST-only."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import httpx

from hivemind.backend.dispatcher import RestUnavailableError

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient

_VALID_PERIODS = frozenset({"daily", "weekly", "monthly", "quarterly", "yearly"})
_VALID_ACTIONS = frozenset({"read", "append", "replace", "delete"})
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


async def build_periodic_response(
    dispatcher: Dispatcher,
    client: ObsidianRestClient,
    *,
    period: str,
    action: str = "read",
    content: str = "",
    date: str = "",
) -> str:
    try:
        dispatcher.require_rest("hive_periodic")
    except RestUnavailableError as exc:
        return str(exc)

    if period not in _VALID_PERIODS:
        valid_p = ", ".join(sorted(_VALID_PERIODS))
        return json.dumps({"error": f"Invalid period '{period}'. Must be: {valid_p}"})
    if action not in _VALID_ACTIONS:
        valid_a = ", ".join(sorted(_VALID_ACTIONS))
        return json.dumps({"error": f"Invalid action '{action}'. Must be: {valid_a}"})
    if date and not _DATE_RE.match(date):
        return json.dumps({"error": "date must be YYYY-MM-DD format"})

    try:
        if action == "read":
            result: dict[str, Any] | str = await client.get_periodic(
                period, date=date, as_json=True
            )
            if isinstance(result, dict):
                return json.dumps({
                    "path": result.get("path", ""),
                    "content": result.get("content", ""),
                    "success": True,
                    "http_status": 200,
                }, indent=2)
            return json.dumps({
                "path": "",
                "content": result,
                "success": True,
                "http_status": 200,
            }, indent=2)

        if action == "append":
            resp = await client.post_periodic(period, content, date=date)
        elif action == "replace":
            resp = await client.put_periodic(period, content, date=date)
        else:
            resp = await client.delete_periodic(period, date=date)

        return json.dumps({
            "success": True,
            "http_status": resp.status_code,
        }, indent=2)

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return json.dumps({
                "error": f"No {period} note found for the requested date",
                "success": False,
                "http_status": 404,
            }, indent=2)
        raise
