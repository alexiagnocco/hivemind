"""hive_retrieve tool — hybrid composite-score + dense-vector retrieval.

Stage 1 fuses the keyword composite with dense cosine similarity (when an
embedding store is available); stage 2 re-ranks by MemRL utility.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from hivemind.projection import project_items, resolve_detail, to_json
from hivemind.scoring.memrl import log_retrieval, memrl_writes_allowed
from hivemind.scoring.retrieve import retrieve, retrieve_chunks

if TYPE_CHECKING:
    from hivemind.config import Settings
    from hivemind.model.note import Note
    from hivemind.rest.connection import ConnectionMonitor
    from hivemind.state.chunk_store import ChunkStore
    from hivemind.state.embedding_store import EmbeddingStore
    from hivemind.state.manifest_cache import ManifestCache
    from hivemind.state.utility import UtilityCache

logger = logging.getLogger(__name__)

_MAX_RESULTS_CAP = 100


def build_retrieve_response(
    cache: ManifestCache,
    utility_cache: UtilityCache,
    settings: Settings,
    *,
    monitor: ConnectionMonitor,
    embedding_store: EmbeddingStore | None = None,
    chunk_store: ChunkStore | None = None,
    query: str = "",
    project: str = "",
    domain: str = "",
    max_results: int = 10,
    include_archived: bool = False,
    detail: str = "standard",
    granularity: str = "note",
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    max_results = min(max_results, _MAX_RESULTS_CAP)

    if granularity not in ("note", "chunk"):
        return to_json(
            {"error": f"Unknown granularity {granularity!r}; use 'note' or 'chunk'"},
            compact=settings.hivemind_profile == "lean",
        )

    if granularity == "chunk":
        return _build_chunk_response(
            manifest.notes,
            utility_cache,
            settings,
            monitor=monitor,
            chunk_store=chunk_store,
            query=query,
            domain=domain,
            max_results=max_results,
            include_archived=include_archived,
            detail=detail,
        )

    note_vectors = None
    query_vector = None
    mode = "keyword"
    # Dense retrieval only applies to text queries; project/domain-only browsing
    # stays on the keyword path.
    if embedding_store is not None and query.strip():
        try:
            note_vectors = embedding_store.index(manifest.notes)
            query_vector = embedding_store.embed_query(query)
            mode = "hybrid"
        except Exception as exc:
            logger.warning("Dense retrieval unavailable (%s); keyword-only", exc)
            note_vectors = None
            query_vector = None
            mode = "keyword"

    scores = utility_cache.load()
    top, rid, gaps = retrieve(
        manifest.notes,
        scores,
        query=query,
        project=project,
        domain=domain,
        max_results=max_results,
        include_archived=include_archived,
        note_vectors=note_vectors,
        query_vector=query_vector,
        dense_weight=settings.hivemind_dense_weight,
        fusion=settings.hivemind_fusion,
    )

    surfaced = [str(c["path"]) for c in top]

    if memrl_writes_allowed(settings, monitor):
        log_retrieval(
            settings.hive_path,
            utility_cache,
            retrieval_id=rid,
            query=query,
            project=project,
            domain=domain,
            surfaced_paths=surfaced,
        )

    tier = resolve_detail(detail, default="standard")
    return to_json(
        {
            "results": project_items(top, tier),
            "count": len(top),
            "mode": mode,
            "gaps": gaps,
            "retrievalId": rid,
        },
        compact=settings.hivemind_profile == "lean",
    )


def _build_chunk_response(
    notes: list[Note],
    utility_cache: UtilityCache,
    settings: Settings,
    *,
    monitor: ConnectionMonitor,
    chunk_store: ChunkStore | None,
    query: str,
    domain: str,
    max_results: int,
    include_archived: bool,
    detail: str,
) -> str:
    compact = settings.hivemind_profile == "lean"
    if chunk_store is None:
        return to_json(
            {"error": "Chunk retrieval unavailable (no chunk store)"}, compact=compact
        )
    if not query.strip():
        return to_json(
            {"error": "granularity='chunk' requires a text query"}, compact=compact
        )

    # Index the FULL note list (the store prunes anything it isn't handed);
    # domain/archive eligibility is applied during scoring.
    chunk_index = chunk_store.index(notes)
    query_vector = None
    mode = "keyword"
    try:
        vec = chunk_store.embed_query(query)
        if vec:
            query_vector = vec
            mode = "hybrid"
    except Exception as exc:
        logger.warning("Dense chunk retrieval unavailable (%s); keyword-only", exc)

    results, rid, gaps = retrieve_chunks(
        notes,
        utility_cache.load(),
        chunk_index,
        query=query,
        domain=domain,
        max_results=max_results,
        include_archived=include_archived,
        query_vector=query_vector,
        dense_weight=settings.hivemind_dense_weight,
        fusion=settings.hivemind_fusion,
    )

    # MemRL joins on parent note paths (deduped, order-preserving).
    surfaced: list[str] = []
    for r in results:
        if r["path"] not in surfaced:
            surfaced.append(str(r["path"]))

    if memrl_writes_allowed(settings, monitor):
        log_retrieval(
            settings.hive_path,
            utility_cache,
            retrieval_id=rid,
            query=query,
            project="",
            domain=domain,
            surfaced_paths=surfaced,
        )

    tier = resolve_detail(detail, default="standard")
    return to_json(
        {
            "results": project_items(results, tier),
            "count": len(results),
            "mode": mode,
            "granularity": "chunk",
            "gaps": gaps,
            "retrievalId": rid,
        },
        compact=compact,
    )
