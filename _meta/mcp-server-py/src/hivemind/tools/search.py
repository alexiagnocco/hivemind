from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hivemind.model.note import note_to_dict
from hivemind.projection import project_items, resolve_detail, to_json
from hivemind.scoring.relevance import match_note

if TYPE_CHECKING:
    from hivemind.backend.dispatcher import Dispatcher
    from hivemind.config import Settings
    from hivemind.rest.client import ObsidianRestClient
    from hivemind.state.manifest_cache import ManifestCache


async def build_search_response(
    cache: ManifestCache,
    settings: Settings,
    *,
    query: str = "",
    domain: str = "",
    tags: str = "",
    note_type: str = "",
    status: str = "",
    project: str = "",
    limit: int = 10,
    slim: bool = True,
    detail: str = "",
    mode: str = "auto",
    dispatcher: Dispatcher | None = None,
    client: ObsidianRestClient | None = None,
) -> str:
    tag_list: list[str] | None = None
    if tags:
        tag_list = [t.strip().lstrip("#") for t in tags.split(",") if t.strip()]

    # slim is the deprecated alias: True -> minimal (default), False -> full.
    tier = resolve_detail(detail, slim=slim, default="minimal")
    compact = settings.hivemind_profile == "lean"

    has_metadata_filter = bool(domain or tag_list or note_type or status or project)

    resolved_mode = mode
    if mode == "auto":
        if has_metadata_filter:
            resolved_mode = "manifest"
        elif dispatcher is not None and client is not None and query:
            from hivemind.backend.dispatcher import Backend

            resolved_mode = (
                "simple" if dispatcher.pick() == Backend.REST else "manifest"
            )
        else:
            resolved_mode = "manifest"

    if resolved_mode == "simple" and dispatcher is not None and client is not None:

        async def rest_fn() -> str:
            return await _search_rest_simple(
                client,
                query=query,
                limit=limit,
                tier=tier,
                compact=compact,
                mode_used="simple",
            )

        async def fs_fn() -> str:
            return _search_manifest(
                cache,
                query=query,
                domain=domain,
                tag_list=tag_list,
                note_type=note_type,
                status=status,
                project=project,
                limit=limit,
                tier=tier,
                compact=compact,
                mode_used="manifest",
            )

        return await dispatcher.perform(rest_fn, fs_fn, tool="hive_search")

    return _search_manifest(
        cache,
        query=query,
        domain=domain,
        tag_list=tag_list,
        note_type=note_type,
        status=status,
        project=project,
        limit=limit,
        tier=tier,
        compact=compact,
        mode_used=resolved_mode,
    )


async def _search_rest_simple(
    client: ObsidianRestClient,
    *,
    query: str,
    limit: int,
    tier: str,
    compact: bool,
    mode_used: str,
) -> str:
    hits = await client.search_simple(query, context_length=100)
    capped = hits[:limit]

    results: list[dict[str, Any]] = [
        {
            "path": hit.get("filename", hit.get("path", "")),
            "score": hit.get("score", 0),
            "matches": hit.get("matches", []),
        }
        for hit in capped
    ]

    return to_json(
        {
            "results": project_items(results, tier),
            "count": len(results),
            "mode_used": mode_used,
        },
        compact=compact,
    )


def _search_manifest(
    cache: ManifestCache,
    *,
    query: str,
    domain: str,
    tag_list: list[str] | None,
    note_type: str,
    status: str,
    project: str,
    limit: int,
    tier: str,
    compact: bool,
    mode_used: str,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    from hivemind.model.note import Note

    results: list[Note] = []
    for note in manifest.notes:
        if match_note(
            note,
            query=query or "",
            domain=domain or "",
            tags=tag_list,
            note_type=note_type or "",
            status=status or "",
            project=project or "",
        ):
            results.append(note)
        if len(results) >= limit:
            break

    output = project_items([note_to_dict(n) for n in results], tier)

    return to_json(
        {"results": output, "count": len(output), "mode_used": mode_used},
        compact=compact,
    )
