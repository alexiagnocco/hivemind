from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
from fastmcp.server.lifespan import lifespan

from engram import __version__
from engram.backend.dispatcher import Dispatcher
from engram.config import Settings
from engram.rest.client import ObsidianRestClient
from engram.rest.connection import ConnectionMonitor
from engram.scoring.embeddings import get_embedding_backend
from engram.state.embedding_store import EmbeddingStore
from engram.state.manifest_cache import ManifestCache
from engram.state.utility import UtilityCache
from engram.tools.active import build_active_response
from engram.tools.checkpoint import build_checkpoint_response
from engram.tools.command import build_command_response
from engram.tools.context import build_context_response
from engram.tools.document_map import build_document_map_response
from engram.tools.feedback import build_feedback_response
from engram.tools.health import build_health_response
from engram.tools.manifest_tool import build_manifest_response
from engram.tools.open import build_open_response
from engram.tools.patch import build_patch_response
from engram.tools.periodic import build_periodic_response
from engram.tools.prune_dryrun import build_prune_dryrun_response
from engram.tools.read import build_read_response
from engram.tools.recent import build_recent_response
from engram.tools.related import build_related_response
from engram.tools.retrieve import build_retrieve_response
from engram.tools.search import build_search_response
from engram.tools.session_check import build_session_check_response
from engram.tools.sigma_rho import build_sigma_rho_response
from engram.tools.status import build_status_response
from engram.tools.tags import build_tags_response
from engram.tools.unmined_sessions import build_unmined_sessions_response

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
    manifest_cache = ManifestCache(settings.vault_path)
    utility_cache = UtilityCache(settings.vault_path)
    dispatcher = Dispatcher(mode=settings.obsidian_fallback_mode, monitor=monitor)

    embedding_store: EmbeddingStore | None = None
    backend = get_embedding_backend(settings)
    if backend is not None:
        embedding_store = EmbeddingStore(settings.vault_path, backend)
        logger.info("Hybrid retrieval enabled (embedding backend: %s)", backend.name)
    else:
        logger.info("Hybrid retrieval disabled; vault_retrieve is keyword-only")

    await monitor.start()

    logger.info(
        "engram started: state=%s fallback=%s",
        monitor.current_state,
        settings.obsidian_fallback_mode,
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
        }
    finally:
        logger.info("Shutting down engram")
        await client.aclose()
        await monitor.stop()


mcp = FastMCP("engram", version=__version__, lifespan=app_lifespan)


# ---------------------------------------------------------------------------
# Phase 1 tool
# ---------------------------------------------------------------------------


@mcp.tool
def vault_status(ctx: Context) -> str:
    """Connection status, plugin version, and server health.

    Returns the current REST connection state (CONNECTED, DEGRADED,
    DISCONNECTED, UNCONFIGURED, or DISABLED), plugin version, fallback
    mode, any active error, and the active embedding backend identity
    (name + dim). The backend name makes the retrieval mode self-evident:
    an 'onnx:' prefix is real semantic dense retrieval, 'hashing-' is the
    lexical fallback, and null means dense retrieval is disabled.
    """
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
async def vault_search(
    ctx: Context,
    query: str = "",
    domain: str = "",
    tags: str = "",
    type: str = "",  # noqa: A002 — v3 API contract; function body never calls type()
    status: str = "",
    project: str = "",
    limit: int = 10,
    slim: bool = True,
    mode: str = "auto",
) -> str:
    """Search vault notes by metadata filters and/or text query.

    mode: auto (default), manifest, simple (REST fulltext).
    Auto routes metadata-filtered queries to manifest, plain queries to REST when connected.
    """
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_search_response(
        cache,
        query=query,
        domain=domain,
        tags=tags,
        note_type=type,
        status=status,
        project=project,
        limit=limit,
        slim=slim,
        mode=mode,
        dispatcher=dispatcher,
        client=client,
    )


@mcp.tool
async def vault_read(ctx: Context, paths: str) -> str:
    """Read the full content of one or more vault notes by comma-separated relative paths."""
    settings: Settings = ctx.lifespan_context["settings"]
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_read_response(
        settings.vault_path, paths=paths, dispatcher=dispatcher, client=client
    )


@mcp.tool
def vault_recent(
    ctx: Context,
    days: int = 7,
    domain: str = "",
    limit: int = 50,
    slim: bool = True,
) -> str:
    """Get notes modified in the last N days."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_recent_response(cache, days=days, domain=domain, limit=limit, slim=slim)


@mcp.tool
def vault_related(ctx: Context, note: str) -> str:
    """Get bidirectional link neighbors for a note."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_related_response(cache, note_ref=note)


@mcp.tool
def vault_manifest(ctx: Context, slim: bool = True) -> str:
    """Return the vault manifest index. slim=true returns essential fields only."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_manifest_response(cache, slim=slim)


@mcp.tool
def vault_rebuild(ctx: Context) -> str:
    """Trigger a manifest rebuild from vault contents (native Python)."""
    from engram.manifest.builder import build_and_write_manifest

    settings: Settings = ctx.lifespan_context["settings"]
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    try:
        summary = build_and_write_manifest(settings.vault_path)
        cache.invalidate()
        return f"Manifest rebuilt successfully (Python v4).\n{summary}"
    except Exception as exc:
        return f"Manifest rebuild failed: {exc}"


# ---------------------------------------------------------------------------
# Phase 3 tools — REST-native (no FS fallback)
# ---------------------------------------------------------------------------


@mcp.tool
async def vault_document_map(ctx: Context, path: str) -> str:
    """Get heading/block/frontmatter skeleton for a note. Requires REST (Obsidian running)."""
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_document_map_response(dispatcher, client, path=path)


@mcp.tool
async def vault_tags(ctx: Context) -> str:
    """List all tags with hierarchical counts. Requires REST (Obsidian running)."""
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_tags_response(dispatcher, client)


@mcp.tool
async def vault_active(
    ctx: Context, action: str = "read", content: str = ""
) -> str:
    """Read, append to, or replace the currently-open note in Obsidian. Requires REST.

    action: read | append | replace.
    """
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_active_response(
        dispatcher, client, action=action, content=content
    )


# ---------------------------------------------------------------------------
# Phase 4 tools — MemRL + health scoring layer
# ---------------------------------------------------------------------------


@mcp.tool
def vault_retrieve(
    ctx: Context,
    query: str = "",
    project: str = "",
    domain: str = "",
    max_results: int = 10,
    include_archived: bool = False,
) -> str:
    """Hybrid composite-score + dense-vector retrieval with re-ranking.

    Stage 1 fuses the keyword composite (match*3 + freshness*2 + connectivity*1)
    with dense-vector cosine similarity, so conceptually relevant notes surface
    even with no keyword overlap. Stage 2 re-ranks by MemRL utility:
    z_norm(base) + w*z_norm(dense), then + lambda*z_norm(utility). Falls back to
    keyword-only when no embedding backend is configured or the query is empty.
    """
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    monitor: ConnectionMonitor = ctx.lifespan_context["monitor"]
    embedding_store: EmbeddingStore | None = ctx.lifespan_context.get("embedding_store")
    return build_retrieve_response(
        cache,
        utility_cache,
        settings,
        monitor=monitor,
        embedding_store=embedding_store,
        query=query,
        project=project,
        domain=domain,
        max_results=max_results,
        include_archived=include_archived,
    )


@mcp.tool
def vault_health(
    ctx: Context,
    window_days: int = 7,
    stale_threshold_days: int = 30,
) -> str:
    """Compute knowledge health metrics: K, I(t), delta, sigma, rho, phi, escape velocity, dK/dt."""
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
def vault_context(
    ctx: Context,
    project: str = "",
    domain: str = "",
    query: str = "",
    max_results: int = 10,
    slim: bool = True,
) -> str:
    """Pre-session context loader. Surfaces relevant vault knowledge for session start."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    return build_context_response(
        cache,
        settings,
        project=project,
        domain=domain,
        query=query,
        max_results=max_results,
        slim=slim,
    )


@mcp.tool
def vault_session_check(
    ctx: Context,
    project: str = "",
    since_minutes: int = 120,
) -> str:
    """Post-session validation: checks that knowledge was persisted properly."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_session_check_response(cache, project=project, since_minutes=since_minutes)


@mcp.tool
def vault_feedback(
    ctx: Context,
    paths: str = "",
    helpful: bool = True,
    retrieval_id: str = "",
) -> str:
    """Record whether retrieved notes were actually helpful (MemRL feedback).

    Updates utility scores via EMA. Writes only when REST is CONNECTED.
    """
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


@mcp.tool
def vault_sigma_rho(ctx: Context) -> str:
    """Compute true sigma and rho from MemRL feedback data."""
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    utility_cache: UtilityCache = ctx.lifespan_context["utility_cache"]
    settings: Settings = ctx.lifespan_context["settings"]
    return build_sigma_rho_response(cache, utility_cache, settings)


@mcp.tool
def vault_prune_dryrun(
    ctx: Context,
    stale_days: int = 30,
    inbox_days: int = 7,
    meta_days: int = 14,
    include_candidates: bool = False,
) -> str:
    """Dry-run prune scan: count candidates by category without moving anything.

    Categories: stale (>N days in projects/resources), completed (done/archived
    in 10-projects), empty (tiny notes with no summary), inbox_aging (old inbox
    items), meta_artifact (old accepted/rejected proposals).
    """
    cache: ManifestCache = ctx.lifespan_context["manifest_cache"]
    return build_prune_dryrun_response(
        cache,
        stale_days=stale_days,
        inbox_days=inbox_days,
        meta_days=meta_days,
        include_candidates=include_candidates,
    )


@mcp.tool
def vault_unmined_sessions(ctx: Context, slim: bool = True) -> str:
    """Check for unmined sessions that should be processed for knowledge extraction."""
    settings: Settings = ctx.lifespan_context["settings"]
    return build_unmined_sessions_response(settings, slim=slim)


# ---------------------------------------------------------------------------
# Phase 5 tools — checkpoint + write operations
# ---------------------------------------------------------------------------


@mcp.tool
async def vault_checkpoint(
    ctx: Context,
    project: str = "",
    summary: str = "",
    decisions: str = "",
    blockers: str = "",
) -> str:
    """Mid-session incremental project memory update.

    Appends a timestamped checkpoint to memory/projects/<project>.md.
    REST path uses surgical PATCH; FS fallback uses file append.
    """
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


@mcp.tool
async def vault_patch(
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

    target_type: heading | block | frontmatter.
    operation: append | prepend | replace.
    apply_if_content_preexists: guard for idempotent appends.
    """
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


@mcp.tool
async def vault_periodic(
    ctx: Context,
    period: str = "",
    action: str = "read",
    content: str = "",
    date: str = "",
) -> str:
    """Daily/weekly/monthly/quarterly/yearly note CRUD. Requires REST.

    period: daily | weekly | monthly | quarterly | yearly.
    action: read | append | replace | delete.
    """
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


@mcp.tool
async def vault_command(
    ctx: Context,
    action: str = "list",
    command_id: str = "",
) -> str:
    """List or run Obsidian commands. Requires REST.

    action: list | run. command_id required for run.
    """
    dispatcher: Dispatcher = ctx.lifespan_context["dispatcher"]
    client: ObsidianRestClient = ctx.lifespan_context["client"]
    return await build_command_response(
        dispatcher, client, action=action, command_id=command_id
    )


@mcp.tool
async def vault_open(
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
    level = getattr(logging, settings.engram_log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger("engram")
    root.setLevel(level)
    root.addHandler(handler)

    if settings.engram_log_file:
        log_path = settings.vault_path / settings.engram_log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setFormatter(handler.formatter)
        root.addHandler(file_handler)
