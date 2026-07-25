from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hivemind.fs.hive_io import read_notes

if TYPE_CHECKING:
    from pathlib import Path

    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.rest.client import ObsidianRestClient


async def build_read_response(
    hive_path: Path,
    *,
    paths: str,
    dispatcher: Dispatcher | None = None,
    client: ObsidianRestClient | None = None,
) -> str:
    path_list = [p.strip() for p in paths.split(",") if p.strip()]
    if not path_list:
        return "ERROR: No paths provided"

    if dispatcher is None:
        return read_notes(hive_path, path_list)

    async def rest_fn() -> str:
        if client is None:
            return read_notes(hive_path, path_list)
        parts: list[str] = []
        for rel_path in path_list:
            result: dict[str, Any] | str = await client.get_note(rel_path.strip())
            content = result if isinstance(result, str) else str(result)
            if len(path_list) > 1:
                parts.append(f"=== {rel_path.strip()} ===\n{content}")
            else:
                parts.append(content)
        return "\n\n".join(parts)

    async def fs_fn() -> str:
        return read_notes(hive_path, path_list)

    return await dispatcher.perform(rest_fn, fs_fn, tool="hive_read")
