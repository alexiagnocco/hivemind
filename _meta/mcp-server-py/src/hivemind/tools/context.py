"""hive_context tool — pre-session context loader and one-shot answer pack.

Beyond the classic context keys (project memory, context notes, activity
counters), a query- or project-scoped call also returns scored ``hits``
(top-5), the top hit's link-graph ``related`` neighbors (paths only), and a
``retrievalId`` routed through the MemRL retrieval log — so a single
hive_context call can anchor, retrieve, expand, and close the feedback loop.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from hivemind.model.note import note_to_dict
from hivemind.projection import project_items, resolve_detail, to_json
from hivemind.scoring.memrl import log_retrieval, memrl_writes_allowed
from hivemind.scoring.relevance import match_score
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

_HITS_CAP = 5
_RELATED_CAP = 5
# Chunk-hit excerpts in the context pack are shorter than hive_retrieve's
# 400 chars — the pack must fit the <=1200-token one-shot budget.
_CONTEXT_EXCERPT_CHARS = 200


def _related_paths(notes: list[Note], top_path: str, cap: int = _RELATED_CAP) -> list[str]:
    """Bidirectional link neighbors of ``top_path``, as paths only."""
    target = next((n for n in notes if n.path == top_path), None)
    if target is None:
        return []
    out_targets = set(target.outLinks or [])
    target_basename = target.basename or target.title
    neighbors: list[str] = []
    for n in notes:
        if n.path == target.path:
            continue
        if (n.basename or n.title) in out_targets or target_basename in (n.outLinks or []):
            neighbors.append(n.path)
        if len(neighbors) >= cap:
            break
    return neighbors


def _note_hits(
    notes: list[Note],
    utility_cache: UtilityCache,
    settings: Settings,
    embedding_store: EmbeddingStore | None,
    *,
    query: str,
    project: str,
    domain: str,
) -> tuple[list[dict[str, Any]], str]:
    note_vectors = None
    query_vector = None
    if embedding_store is not None and query.strip():
        try:
            note_vectors = embedding_store.index(notes)
            query_vector = embedding_store.embed_query(query)
        except Exception as exc:
            logger.warning("Dense retrieval unavailable (%s); keyword-only", exc)
            note_vectors = None
            query_vector = None

    top, retrieval_id, _gaps = retrieve(
        notes,
        utility_cache.load(),
        query=query,
        project=project,
        domain=domain,
        max_results=_HITS_CAP,
        note_vectors=note_vectors,
        query_vector=query_vector,
        dense_weight=settings.hivemind_dense_weight,
        fusion=settings.hivemind_fusion,
    )
    hits = [
        {
            "path": r["path"],
            "title": r["title"],
            "score": r["score"],
            "utility": r["utility"],
        }
        for r in top
    ]
    return hits, retrieval_id


def _chunk_hits(
    notes: list[Note],
    utility_cache: UtilityCache,
    settings: Settings,
    chunk_store: ChunkStore,
    *,
    query: str,
    domain: str,
) -> tuple[list[dict[str, Any]], str]:
    chunk_index = chunk_store.index(notes)
    query_vector = None
    try:
        vec = chunk_store.embed_query(query)
        if vec:
            query_vector = vec
    except Exception as exc:
        logger.warning("Dense chunk retrieval unavailable (%s); keyword-only", exc)

    top, retrieval_id, _gaps = retrieve_chunks(
        notes,
        utility_cache.load(),
        chunk_index,
        query=query,
        domain=domain,
        max_results=_HITS_CAP,
        query_vector=query_vector,
        dense_weight=settings.hivemind_dense_weight,
        fusion=settings.hivemind_fusion,
    )
    hits = [
        {
            "path": r["path"],
            "anchor": r["anchor"],
            "title": r["title"],
            "section": r["section"],
            "score": r["score"],
            "excerpt": str(r["excerpt"])[:_CONTEXT_EXCERPT_CHARS],
            "utility": r["utility"],
        }
        for r in top
    ]
    return hits, retrieval_id


def build_context_response(
    cache: ManifestCache,
    settings: Settings,
    *,
    utility_cache: UtilityCache | None = None,
    monitor: ConnectionMonitor | None = None,
    embedding_store: EmbeddingStore | None = None,
    chunk_store: ChunkStore | None = None,
    project: str = "",
    domain: str = "",
    query: str = "",
    max_results: int = 10,
    slim: bool = True,
    detail: str = "",
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    seen: set[str] = set()
    context_notes: list[Any] = []

    def add_note(n: Any) -> None:
        if n.path not in seen:
            seen.add(n.path)
            context_notes.append(n)

    project_memory: dict[str, Any] | None = None
    if project:
        mem_path = f"memory/projects/{project}.md"
        full_mem = (settings.hive_path / mem_path).resolve()
        if not full_mem.is_relative_to(settings.hive_path.resolve()):
            return json.dumps({"error": "Invalid project slug"})
        if full_mem.exists():
            try:
                content = full_mem.read_text(encoding="utf-8")
                excerpt = 2000 if slim else 10000
                project_memory = {
                    "path": mem_path,
                    "exists": True,
                    "recent_content": content[-excerpt:],
                }
            except Exception:
                project_memory = {"path": mem_path, "exists": False}
        else:
            project_memory = {"path": mem_path, "exists": False}

        for n in manifest.notes:
            if match_score(n, "", project) > 0:
                add_note(n)

    if domain:
        for n in manifest.notes:
            if n.domain == domain:
                add_note(n)

    if query:
        for n in manifest.notes:
            if match_score(n, query, "") > 0:
                add_note(n)

    context_notes.sort(key=lambda n: n.updated or "", reverse=True)
    capped = context_notes[:max_results]

    cutoff_7d = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_count = len([n for n in manifest.notes if (n.updated or "") >= cutoff_7d])
    inbox_count = len([n for n in manifest.notes if n.path.startswith("00-inbox/")])

    # slim is the deprecated alias: True -> minimal (default), False -> full.
    tier = resolve_detail(detail, slim=slim, default="minimal")
    context_output = project_items([note_to_dict(n) for n in capped], tier)

    # One-shot answer pack: scored hits + top-hit neighbors + a logged
    # retrievalId, so the session's first (often only) vault call already
    # closes the MemRL loop via hive_feedback.
    hits: list[dict[str, Any]] = []
    related: list[str] = []
    retrieval_id = ""
    if (query or project) and utility_cache is not None:
        if chunk_store is not None and query.strip():
            # Chunk-level hits: section anchors + short excerpts, so the pack
            # can answer directly without a follow-up hive_read.
            hits, retrieval_id = _chunk_hits(
                manifest.notes, utility_cache, settings, chunk_store,
                query=query, domain=domain,
            )
        else:
            hits, retrieval_id = _note_hits(
                manifest.notes, utility_cache, settings, embedding_store,
                query=query, project=project, domain=domain,
            )
        if hits:
            related = _related_paths(manifest.notes, str(hits[0]["path"]))

        if monitor is not None and memrl_writes_allowed(settings, monitor):
            # Chunk hits can share a parent note — MemRL joins on note paths,
            # so dedupe while preserving rank order.
            surfaced: list[str] = []
            for h in hits:
                if str(h["path"]) not in surfaced:
                    surfaced.append(str(h["path"]))
            log_retrieval(
                settings.hive_path,
                utility_cache,
                retrieval_id=retrieval_id,
                query=query,
                project=project,
                domain=domain,
                surfaced_paths=surfaced,
            )

    result: dict[str, Any] = {
        "project_memory": project_memory,
        "context_notes": context_output,
        "context_count": len(capped),
        "recent_activity_7d": recent_count,
        "inbox_count": inbox_count,
        "nudge": f"Inbox has {inbox_count} items — consider /process-inbox"
        if inbox_count > 5
        else None,
        "hits": hits,
        "related": related,
        "retrievalId": retrieval_id,
    }

    return to_json(result, compact=settings.hivemind_profile == "lean")
