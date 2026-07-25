from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
from fastmcp.server.lifespan import lifespan

from hivemind import __version__
from hivemind.backend.dispatcher import Dispatcher
from hivemind.config import Settings
from hivemind.rest.client import ObsidianRestClient
from hivemind.rest.connection import ConnectionMonitor
from hivemind.scoring.embeddings import get_embedding_backend
from hivemind.state.chunk_store import ChunkStore
from hivemind.state.embedding_store import EmbeddingStore
from hivemind.state.manifest_cache import ManifestCache
from hivemind.state.utility import UtilityCache
from hivemind.tools.active import build_active_response
from hivemind.tools.checkpoint import build_checkpoint_response
from hivemind.tools.command import build_command_response
from hivemind.tools.context import build_context_response
from hivemind.tools.document_map import build_document_map_response
from hivemind.tools.feedback import build_feedback_response
from hivemind.tools.health import build_health_response
from hivemind.tools.manifest_tool import build_manifest_response
from hivemind.tools.open import build_open_response
from hivemind.tools.patch import build_patch_response
from hivemind.tools.periodic import build_periodic_response
from hivemind.tools.prune_dryrun import build_prune_dryrun_response
from hivemind.tools.read import build_read_response
from hivemind.tools.recent import build_recent_response
from hivemind.tools.related import build_related_response
from hivemind.tools.retrieve import build_retrieve_response
from hivemind.tools.search import build_search_response
from hivemind.tools.session_check import build_session_check_response
from hivemind.tools.sigma_rho import build_sigma_rho_response
from hivemind.tools.status import build_status_response
from hivemind.tools.tags import build_tags_response
from hivemind.tools.unmined_sessions import build_unmined_sessions_response

logger = logging.getLogger(__name__)


@lifespan
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    settings = Settings()
    _setup_logging(settings)

    unconfigured = not settings.obsidian_api_key
    client = ObsidianRestClient(settings)
    monitor = ConnectionMonitor(
        client,
        interval=settings.obsidian_recheck_interval_sec,
        unconfigured=unconfigured,
    )
    manifest_cache = ManifestCache(settings.hive_path)
    utility_cache = UtilityCache(settings.hive_path)

    # The manifest is a derived index (gitignored), so fresh clones start
    # without one — build it on startup rather than failing every tool call.
    if not (settings.hive_path / "_meta" / "hive-manifest.json").exists():
        from hivemind.manifest.builder import build_and_write_manifest

        try:
            summary = build_and_write_manifest(settings.hive_path)
            logger.info("No manifest found; built one at startup. %s", summary)
        except Exception:
            logger.warning("Startup manifest build failed", exc_info=True)
    dispatcher = Dispatcher(mode=settings.obsidian_fallback_mode, monitor=monitor)

    embedding_store: EmbeddingStore | None = None
    backend = get_embedding_backend(settings)
    if backend is not None:
        embedding_store = EmbeddingStore(settings.hive_path, backend)
        logger.info("Hybrid retrieval enabled (embedding backend: %s)", backend.name)
    else:
        logger.info("Hybrid retrieval disabled; hive_retrieve is keyword-only")
    # Chunk-granularity retrieval works with or without a dense backend
    # (keyword-only chunk scoring when backend is None). Built lazily on first
    # chunk query; hive_rebuild pre-warms it.
    chunk_store = ChunkStore(settings.hive_path, backend)

    await monitor.start()

    logger.info(
        "hivemind started: state=%s fallback=%s profile=%s",
        monitor.current_state,
        settings.obsidian_fallback_mode,
        _PROFILE,
    )

    try:
        yield {
            "settings": settings,
            "client": client,
            "monitor": monitor,
            "manifest_cache": manifest_cache,
            "utility_cache": utility_cache,
            "dispatcher": dispatcher,
            "embedding_store": embedding_store,
            "chunk_store": chunk_store,
        }
    finally:
        logger.info("Shutting down hivemind")
        await client.aclose()
        await monitor.stop()


mcp = FastMCP("hivemind", version=__version__, lifespan=app_lifespan)

# Tool registration happens at import (@mcp.tool decorators), so the profile
# must be read from the environment here — Settings.hivemind_profile mirrors
# it for runtime consumers. "lean" registers only the 8 core tools, keeping
# the standing tool-description payload minimal for token-metered clients.
_PROFILE = os.environ.get("HIVEMIND_PROFILE", "full").strip().lower()
if _PROFILE not in ("full", "lean"):
    logger.warning("Unknown HIVEMIND_PROFILE %r; defaulting to 'full'", _PROFILE)
    _PROFILE = "full"
# Write the normalized value back so Settings (env beats .env file) always
# agrees with the tool surface actually registered below.
os.environ["HIVEMIND_PROFILE"] = _PROFILE


def _full_only(fn: Callable[..., Any]) -> Any:
    """Register a tool only in the full profile; lean leaves it unregistered."""
    return mcp.tool(fn) if _PROFILE == "full" else fn


# ---------------------------------------------------------------------------
# Phase 1 tool
# ---------------------------------------------------------------------------


@mcp.tool
def hive_status(ctx: Context) -> str:
    """Connection status, plugin version, fallback mode, and embedding backend
    ('onnx:'=semantic, 'hashing-'=lexical fallback, null=dense disabled)."""
    settings: Settings = ctx.lifespan_context["settings"]
    monitor: ConnectionMonitor = ctx.lifespan_context["monitor"]
    embedding_store: EmbeddingStore | None = ctx.lifespan_context.get("embedding_store")
    return build_status_response(
        settings,
        monitor,
        backend=embedding_store.backend if embedding_store is not None else None,
    )


# ---------------------------------------------------------------------------
# Phase 2 tools — FS path (manifest-based)
# ---------------------------------------------------------------------------


@mcp.tool
async def hive_search(
    ctx: Context,
    query: str = "",
    domain: str = "",
    tags: str = "",
    type: str = "",  # noqa: A002 — v3 API contract; function body never calls type()
    status: str = "",
    project: str = "",
    limit: int = 10,
    slim: bool = True,
    detail: str = "",
    mode: str = "auto",
) -> str:
    """Search notes by metadata filters and/or text. detail: minimal|standard|full
    (slim is a deprecated alias). mode: auto|manifest|simple (REST fulltext)."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_search_response(
        cache,
        settings,
        query=query,
        domain=domain,
        tags=tags,
        note_type=type,
        status=status,
        project=project,
        limit=limit,
        slim=slim,
        detail=detail,
        mode=mode,
        dispatcher=dispatcher,
        client=client,
    )


@mcp.tool
async def hive_read(ctx: Context, paths: str) -> str:
    """Read full note content by comma-separated relative paths."""
    settings: Settings = ctx.lifespan_context["settings"]
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_read_response(
        settings.hive_path, paths=paths, dispatcher=dispatcher, client=client
    )


@_full_only
def hive_recent(
    ctx: Context,
    days: int = 7,
    domain: str = "",
    limit: int = 50,
    slim: bool = True,
) -> str:
    """List notes modified in the last N days, optional domain filter."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_recent_response(cache, days=days, domain=domain, limit=limit, slim=slim)


@mcp.tool
def hive_related(ctx: Context, note: str) -> str:
    """Bidirectional link-graph neighbors for a note."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_related_response(cache, note_ref=note)


@_full_only
def hive_manifest(ctx: Context, slim: bool = True) -> str:
    """Full manifest index (slim=true trims fields). Heavy — never use for
    per-query context; prefer hive_search or hive_retrieve."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_manifest_response(cache, slim=slim)


@mcp.tool
def hive_rebuild(ctx: Context) -> str:
    """Rebuild the manifest index and pre-warm the derived retrieval indexes
    (note embeddings + chunk index) so the next hive_retrieve is instant."""
    from hivemind.manifest.builder import build_and_write_manifest

    settings: Settings = ctx.lifespan_context["settings"]
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    embedding_store: EmbeddingStore | None = ctx.lifespan_context.get("embedding_store")
    chunk_store: ChunkStore | None = ctx.lifespan_context.get("chunk_store")
    try:
        summary = build_and_write_manifest(settings.hive_path)
        cache.invalidate()
    except Exception as exc:
        return f"Manifest rebuild failed: {exc}"

    warm = ""
    try:
        manifest = cache.load()
        if not manifest.error:
            if embedding_store is not None:
                embedding_store.index(manifest.notes)
            if chunk_store is not None:
                chunk_count = sum(
                    len(v) for v in chunk_store.index(manifest.notes).values()
                )
                warm = f"\n  Chunk index warmed: {chunk_count} chunks"
    except Exception as exc:
        warm = f"\n  Index pre-warm skipped: {exc}"

    return f"Manifest rebuilt successfully (Python v4).\n{summary}{warm}"


# ---------------------------------------------------------------------------
# Phase 3 tools — REST-native (no FS fallback)
# ---------------------------------------------------------------------------


@_full_only
async def hive_document_map(ctx: Context, path: str) -> str:
    """Heading/block/frontmatter skeleton for a note. Requires REST (Obsidian running)."""
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_document_map_response(dispatcher, client, path=path)


@_full_only
async def hive_tags(ctx: Context) -> str:
    """List all tags with hierarchical counts. Requires REST (Obsidian running)."""
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_tags_response(dispatcher, client)


@_full_only
async def hive_active(
    ctx: Context, action: str = "read", content: str = ""
) -> str:
    """Read, append to, or replace the currently-open Obsidian note. Requires REST.
    action: read|append|replace."""
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_active_response(
        dispatcher, client, action=action, content=content
    )


# ---------------------------------------------------------------------------
# Phase 4 tools — MemRL + health scoring layer
# ---------------------------------------------------------------------------


@mcp.tool
def hive_retrieve(
    ctx: Context,
    query: str = "",
    project: str = "",
    domain: str = "",
    max_results: int = 10,
    include_archived: bool = False,
    detail: str = "standard",
    granularity: str = "note",
) -> str:
    """Hybrid keyword+dense retrieval (RRF fusion) re-ranked by MemRL utility
    (keyword-only without embeddings or query). detail: minimal|standard|full.
    granularity: note|chunk (chunk needs a query; <=5 anchored section hits).
    Returns retrievalId — close the loop with hive_feedback."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    monitor: ConnectionMonitor = ctx.lifespan_context["monitor"]
    embedding_store: EmbeddingStore | None = ctx.lifespan_context.get("embedding_store")
    chunk_store: ChunkStore | None = ctx.lifespan_context.get("chunk_store")
    return build_retrieve_response(
        cache,
        utility_cache,
        settings,
        monitor=monitor,
        embedding_store=embedding_store,
        chunk_store=chunk_store,
        query=query,
        project=project,
        domain=domain,
        max_results=max_results,
        include_archived=include_archived,
        detail=detail,
        granularity=granularity,
    )


@_full_only
def hive_health(
    ctx: Context,
    window_days: int = 7,
    stale_threshold_days: int = 30,
) -> str:
    """Knowledge health metrics: K, I(t), delta, sigma, rho, phi, escape velocity, dK/dt."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    return build_health_response(
        cache,
        utility_cache,
        settings,
        window_days=window_days,
        stale_threshold_days=stale_threshold_days,
    )


@mcp.tool
def hive_context(
    ctx: Context,
    project: str = "",
    domain: str = "",
    query: str = "",
    max_results: int = 10,
    slim: bool = True,
    detail: str = "",
) -> str:
    """One-shot pre-session context: project memory + relevant notes + activity,
    plus scored hits, top-hit link neighbors, and a logged retrievalId when a
    query/project is given. Start sessions here. detail: minimal|standard|full."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    monitor: ConnectionMonitor = ctx.lifespan_context["monitor"]
    embedding_store: EmbeddingStore | None = ctx.lifespan_context.get("embedding_store")
    chunk_store: ChunkStore | None = ctx.lifespan_context.get("chunk_store")
    return build_context_response(
        cache,
        settings,
        utility_cache=utility_cache,
        monitor=monitor,
        embedding_store=embedding_store,
        chunk_store=chunk_store,
        project=project,
        domain=domain,
        query=query,
        max_results=max_results,
        slim=slim,
        detail=detail,
    )


@_full_only
def hive_session_check(
    ctx: Context,
    project: str = "",
    since_minutes: int = 120,
) -> str:
    """Post-session validation that new knowledge was persisted (notes, orphans,
    frontmatter, project memory)."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_session_check_response(cache, project=project, since_minutes=since_minutes)


@mcp.tool
def hive_feedback(
    ctx: Context,
    paths: str = "",
    helpful: bool = True,
    retrieval_id: str = "",
) -> str:
    """Record whether retrieved notes helped (MemRL EMA update). Pass paths plus
    the retrieval_id from hive_retrieve — skipping this stales the ranker."""
    if not paths.strip():
        return '{"error": "paths parameter is required"}'
    monitor: ConnectionMonitor = ctx.lifespan_context["monitor"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    return build_feedback_response(
        utility_cache,
        settings,
        monitor=monitor,
        paths=paths,
        helpful=helpful,
        retrieval_id=retrieval_id,
    )


@_full_only
def hive_sigma_rho(ctx: Context) -> str:
    """Compute measured sigma/rho from accumulated MemRL feedback."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    return build_sigma_rho_response(cache, utility_cache, settings)


@_full_only
def hive_prune_dryrun(
    ctx: Context,
    stale_days: int = 30,
    inbox_days: int = 7,
    meta_days: int = 14,
    include_candidates: bool = False,
) -> str:
    """Dry-run prune scan: counts stale/completed/empty/inbox-aging/meta
    candidates. Moves nothing."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_prune_dryrun_response(
        cache,
        stale_days=stale_days,
        inbox_days=inbox_days,
        meta_days=meta_days,
        include_candidates=include_candidates,
    )


@_full_only
def hive_unmined_sessions(ctx: Context, slim: bool = True) -> str:
    """List sessions not yet mined for knowledge extraction."""
    settings: Settings = ctx.lifespan_context["settings"]
    return build_unmined_sessions_response(settings, slim=slim)


# ---------------------------------------------------------------------------
# Phase 5 tools — checkpoint + write operations
# ---------------------------------------------------------------------------


@_full_only
async def hive_checkpoint(
    ctx: Context,
    project: str = "",
    summary: str = "",
    decisions: str = "",
    blockers: str = "",
) -> str:
    """Append a timestamped checkpoint (summary/decisions/blockers) to
    memory/projects/<project>.md."""
    if not project.strip():
        return '{"error": "project parameter is required"}'
    if not summary.strip():
        return '{"error": "summary parameter is required"}'
    settings: Settings = ctx.lifespan_context["settings"]
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_checkpoint_response(
        settings,
        dispatcher,
        client,
        project=project,
        summary=summary,
        decisions=decisions,
        blockers=blockers,
    )


# ---------------------------------------------------------------------------
# Phase 6 tools — REST-only write operations
# ---------------------------------------------------------------------------


@_full_only
async def hive_patch(
    ctx: Context,
    path: str = "",
    target_type: str = "",
    target: str = "",
    content: str = "",
    operation: str = "append",
    target_delimiter: str = "::",
    create_if_missing: bool = False,
    apply_if_content_preexists: str = "",
) -> str:
    """Surgical heading/block/frontmatter edit via REST PATCH. Requires REST.
    target_type: heading|block|frontmatter; operation: append|prepend|replace."""
    if not path.strip():
        return '{"error": "path parameter is required"}'
    if not target_type.strip():
        return '{"error": "target_type parameter is required"}'
    if not target.strip():
        return '{"error": "target parameter is required"}'
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_patch_response(
        dispatcher,
        client,
        path=path,
        target_type=target_type,
        target=target,
        content=content,
        operation=operation,
        target_delimiter=target_delimiter,
        create_if_missing=create_if_missing,
        apply_if_content_preexists=apply_if_content_preexists,
    )


@_full_only
async def hive_periodic(
    ctx: Context,
    period: str = "",
    action: str = "read",
    content: str = "",
    date: str = "",
) -> str:
    """Periodic note CRUD. Requires REST. period: daily|weekly|monthly|quarterly|
    yearly; action: read|append|replace|delete."""
    if not period.strip():
        return '{"error": "period parameter is required"}'
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_periodic_response(
        dispatcher,
        client,
        period=period,
        action=action,
        content=content,
        date=date,
    )


@_full_only
async def hive_command(
    ctx: Context,
    action: str = "list",
    command_id: str = "",
) -> str:
    """List or run Obsidian commands. Requires REST. action: list|run
    (command_id required for run)."""
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_command_response(
        dispatcher, client, action=action, command_id=command_id
    )


@_full_only
async def hive_open(
    ctx: Context,
    path: str = "",
    new_leaf: bool = True,
) -> str:
    """Bring a note into focus in the Obsidian UI. Requires REST."""
    if not path.strip():
        return '{"error": "path parameter is required"}'
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_open_response(
        dispatcher, client, path=path, new_leaf=new_leaf
    )


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging(settings: Settings) -> None:
    level = getattr(logging, settings.hivemind_log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger("hivemind")
    root.setLevel(level)
    root.addHandler(handler)

    if settings.hivemind_log_file:
        log_path = settings.hive_path / settings.hivemind_log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setFormatter(handler.formatter)
        root.addHandler(file_handler)
