"""Hybrid composite-score + dense-vector retrieval with re-ranking.

Two retrieval paths share one entry point:

* **Keyword-only** (no query embedding supplied): the original composite scorer
  — ``match*3 + freshness*2 + connectivity*1`` re-ranked by
  ``zNorm(base) + LAMBDA_UTILITY * zNorm(utility)``. Behavior is unchanged from
  the pre-hybrid implementation, so notes with ``match_score == 0`` are skipped.

* **Hybrid** (a ``query_vector`` and per-note ``note_vectors`` are supplied):
  two stages —

  1. *Candidate generation / fusion.* Every non-archived, in-domain note is a
     candidate (not just keyword matches), so a conceptually relevant note that
     shares no keywords with the query is no longer dropped. The keyword leg
     (candidates ranked by composite base score) and the dense leg (candidates
     ranked by cosine) are fused into one stage-1 score. Fusion strategy is
     selectable via ``fusion``:

     * ``"rrf"`` (default) — Reciprocal Rank Fusion, ``sum(1/(k+rank))`` over
       both legs with a full outer join (a note missing from one leg keeps its
       contribution from the other).
     * ``"znorm"`` — the previous score-level fusion,
       ``zNorm(base) + W_DENSE * zNorm(dense_cosine)``; retained for rollback.

     The top ``pool`` candidates advance.
  2. *Re-ranking.* Within the pool, the stage-1 scores are z-normalized (so
     ``LAMBDA_UTILITY`` stays calibrated regardless of fusion strategy — RRF
     scores live on a much smaller scale than z-scores) and the learned MemRL
     utility signal is folded in:
     ``zNorm(stage1) + LAMBDA_UTILITY * zNorm(utility)``. The top
     ``max_results`` are returned. Under ``znorm`` fusion, stage-1 scores are
     used as-is (already z-scaled), preserving pre-RRF behavior exactly.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from hivemind.scoring.embeddings import cosine
from hivemind.scoring.relevance import (
    LAMBDA_UTILITY,
    POOL_FLOOR,
    POOL_MULTIPLIER,
    RRF_K,
    W_DENSE,
    connectivity_score,
    freshness_score,
    match_score,
    retrieval_id,
    round_val,
    rrf_scores,
    utility_score,
    z_norm,
)

if TYPE_CHECKING:
    from hivemind.model.note import Note
    from hivemind.state.chunk_store import ChunkRecord
    from hivemind.state.utility import UtilityScores

# Chunk-granularity results are capped hard — chunks exist to keep responses
# small, so a large max_results must not reinflate them.
CHUNK_RESULTS_CAP = 5
CHUNK_EXCERPT_CHARS = 400


def retrieve(
    notes: list[Note],
    scores: UtilityScores,
    *,
    query: str = "",
    project: str = "",
    domain: str = "",
    max_results: int = 10,
    include_archived: bool = False,
    note_vectors: dict[str, list[float]] | None = None,
    query_vector: list[float] | None = None,
    dense_weight: float = W_DENSE,
    fusion: str = "rrf",
) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Score, rank, and return the top results with a retrieval ID.

    When ``query_vector`` and ``note_vectors`` are provided the hybrid two-stage
    path runs; otherwise the keyword-only composite path runs. ``fusion``
    selects the hybrid stage-1 strategy: ``"rrf"`` (default) or ``"znorm"``.

    Returns (results, retrieval_id, gaps).
    """
    hybrid = bool(query_vector) and bool(note_vectors)
    rid = retrieval_id()

    if hybrid:
        top = _retrieve_hybrid(
            notes,
            scores,
            query=query,
            project=project,
            domain=domain,
            max_results=max_results,
            include_archived=include_archived,
            note_vectors=note_vectors or {},
            query_vector=query_vector or [],
            dense_weight=dense_weight,
            fusion=fusion,
        )
    else:
        top = _retrieve_keyword(
            notes,
            scores,
            query=query,
            project=project,
            domain=domain,
            max_results=max_results,
            include_archived=include_archived,
        )

    gaps: list[str] = []
    if query and not top:
        gaps.append(f"No vault content found for '{query}'")
    if project and not any("memory/projects" in str(r["path"]) for r in top):
        gaps.append(f"No project memory found for '{project}'")

    return top, rid, gaps


def chunk_match_score(chunk_text_lower: str, query: str) -> int:
    """Lexical match score of a query against one chunk's text.

    Mirrors the note-level heuristic: exact phrase beats word hits, and word
    hits only count when at least half the query words appear.
    """
    if not query:
        return 0
    q = query.lower()
    if q in chunk_text_lower:
        return 4
    words = [w for w in q.split() if len(w) > 1]
    if not words:
        return 0
    matched = sum(1 for w in words if w in chunk_text_lower)
    if matched >= math.ceil(len(words) / 2):
        return matched
    return 0


def _excerpt(text: str, limit: int = CHUNK_EXCERPT_CHARS) -> str:
    stripped = text.strip()
    return stripped[:limit] + "..." if len(stripped) > limit else stripped


def retrieve_chunks(
    notes: list[Note],
    scores: UtilityScores,
    chunk_index: dict[str, list[ChunkRecord]],
    *,
    query: str = "",
    domain: str = "",
    max_results: int = CHUNK_RESULTS_CAP,
    include_archived: bool = False,
    query_vector: list[float] | None = None,
    dense_weight: float = W_DENSE,
    fusion: str = "rrf",
) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Chunk-granularity retrieval: same two-stage shape as note retrieval.

    Stage 1 fuses a keyword leg (lexical chunk match) with a dense leg (cosine
    against CCH-contextualized chunk vectors) via RRF (or znorm). Stage 2
    z-norms the pool and folds in the *parent note's* MemRL utility — feedback
    joins on note paths, so chunks inherit their note's learned signal.

    Results carry ``{path, anchor, title, section, score, excerpt, utility}``
    and are capped at :data:`CHUNK_RESULTS_CAP`. Returns
    (results, retrieval_id, gaps).
    """
    rid = retrieval_id()
    max_results = min(max(max_results, 1), CHUNK_RESULTS_CAP)
    qv = query_vector or []

    candidates: list[dict[str, Any]] = []
    for note in notes:
        if not _eligible(note, domain=domain, include_archived=include_archived):
            continue
        for i, rec in enumerate(chunk_index.get(note.path, [])):
            kw = chunk_match_score(rec.text.lower(), query)
            dense = cosine(qv, rec.vector) if qv and rec.vector else 0.0
            if kw == 0 and dense <= 0.0:
                continue
            candidates.append({
                "id": f"{note.path}#{i}",
                "path": note.path,
                "anchor": rec.anchor,
                "title": note.title or note.basename or "",
                "section": rec.section,
                "excerpt": _excerpt(rec.text),
                "keywordScore": kw,
                "denseScore": round_val(dense, 4),
                "utility": round_val(utility_score(note.path, scores), 3),
            })

    gaps: list[str] = []
    if not candidates:
        if query:
            gaps.append(f"No vault content found for '{query}'")
        return [], rid, gaps

    if fusion == "znorm":
        z_kw = z_norm([float(c["keywordScore"]) for c in candidates])
        z_dense = z_norm([float(c["denseScore"]) for c in candidates])
        for i, cand in enumerate(candidates):
            cand["stage1Score"] = z_kw[i] + dense_weight * z_dense[i]
        renorm_pool = False
    else:
        keyword_leg = sorted(
            (c for c in candidates if int(c["keywordScore"]) > 0),
            key=lambda c: (-float(c["keywordScore"]), str(c["id"])),
        )
        dense_leg = sorted(
            (c for c in candidates if float(c["denseScore"]) > 0.0),
            key=lambda c: (-float(c["denseScore"]), str(c["id"])),
        )
        fused = rrf_scores(
            [[str(c["id"]) for c in keyword_leg], [str(c["id"]) for c in dense_leg]],
            k=RRF_K,
        )
        for cand in candidates:
            cand["stage1Score"] = fused.get(str(cand["id"]), 0.0)
        renorm_pool = True

    candidates.sort(key=lambda c: (-float(c["stage1Score"]), str(c["id"])))
    pool_size = max(max_results * POOL_MULTIPLIER, POOL_FLOOR)
    pool = candidates[:pool_size]

    stage1 = [float(c["stage1Score"]) for c in pool]
    if renorm_pool:
        stage1 = z_norm(stage1)
    z_util = z_norm([float(c["utility"]) for c in pool])
    for i, cand in enumerate(pool):
        cand["score"] = round_val(stage1[i] + LAMBDA_UTILITY * z_util[i], 4)
    pool.sort(key=lambda c: float(c["score"]), reverse=True)

    top = pool[:max_results]
    results = [
        {
            "path": c["path"],
            "anchor": c["anchor"],
            "title": c["title"],
            "section": c["section"],
            "score": c["score"],
            "excerpt": c["excerpt"],
            "utility": c["utility"],
        }
        for c in top
    ]
    return results, rid, gaps


def _candidate(note: Note, scores: UtilityScores, ms: int) -> dict[str, Any]:
    fs = freshness_score(note.updated or "")
    cs = connectivity_score(note)
    base = ms * 3 + fs * 2 + cs * 1
    util = utility_score(note.path, scores)
    return {
        "path": note.path,
        "title": note.title or note.basename or "",
        "baseScore": base,
        "utility": round_val(util, 3),
        "matchScore": ms,
        "freshnessScore": fs,
        "connectivityScore": cs,
        "summary": note.summary or "",
        "updated": note.updated or "",
        "status": note.status or "",
        "inboundLinks": note.inboundCount,
        "isArchived": note.path.startswith("40-archive"),
        "domain": note.domain or "",
        "tags": list(note.tags),
    }


def _eligible(note: Note, *, domain: str, include_archived: bool) -> bool:
    if not include_archived and note.path.startswith("40-archive"):
        return False
    return not (domain and note.domain != domain)


def _retrieve_keyword(
    notes: list[Note],
    scores: UtilityScores,
    *,
    query: str,
    project: str,
    domain: str,
    max_results: int,
    include_archived: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for note in notes:
        if not _eligible(note, domain=domain, include_archived=include_archived):
            continue
        ms = match_score(note, query, project)
        if ms == 0 and (query or project):
            continue
        cand = _candidate(note, scores, ms)
        cand["denseScore"] = 0.0
        cand["mode"] = "keyword"
        candidates.append(cand)

    if candidates:
        z_base = z_norm([float(c["baseScore"]) for c in candidates])
        z_util = z_norm([float(c["utility"]) for c in candidates])
        for i, cand in enumerate(candidates):
            cand["score"] = round_val(z_base[i] + LAMBDA_UTILITY * z_util[i], 4)
        # Ties break by path so ordering never depends on manifest order
        # (parity with the hybrid and chunk paths).
        candidates.sort(key=lambda c: (-float(c["score"]), str(c["path"])))

    return candidates[:max_results]


def _retrieve_hybrid(
    notes: list[Note],
    scores: UtilityScores,
    *,
    query: str,
    project: str,
    domain: str,
    max_results: int,
    include_archived: bool,
    note_vectors: dict[str, list[float]],
    query_vector: list[float],
    dense_weight: float,
    fusion: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for note in notes:
        if not _eligible(note, domain=domain, include_archived=include_archived):
            continue
        ms = match_score(note, query, project)
        vec = note_vectors.get(note.path)
        dense = cosine(query_vector, vec) if vec else 0.0
        # Stage 1 candidate generation: keep keyword matches AND any note with a
        # dense vector, so zero-keyword-but-semantically-relevant notes survive.
        if ms == 0 and dense <= 0.0:
            continue
        cand = _candidate(note, scores, ms)
        cand["denseScore"] = round_val(dense, 4)
        cand["mode"] = "hybrid"
        candidates.append(cand)

    if not candidates:
        return []

    if fusion == "znorm":
        # Score-level fusion (pre-RRF behavior, retained for rollback):
        # z-normalized keyword base plus weighted z-normalized dense cosine.
        # Stage-1 scores are already z-scaled, so stage 2 uses them as-is.
        z_base = z_norm([float(c["baseScore"]) for c in candidates])
        z_dense = z_norm([float(c["denseScore"]) for c in candidates])
        for i, cand in enumerate(candidates):
            cand["stage1Score"] = z_base[i] + dense_weight * z_dense[i]
        renorm_pool = False
    else:
        # Rank-level fusion (RRF): each leg ranks its own matches; a full outer
        # join sums 1/(k+rank) so a note missing from one leg keeps its
        # contribution from the other. Leg order ties break by path for
        # determinism.
        keyword_leg = sorted(
            (c for c in candidates if int(c["matchScore"]) > 0),
            key=lambda c: (-float(c["baseScore"]), str(c["path"])),
        )
        dense_leg = sorted(
            (c for c in candidates if float(c["denseScore"]) > 0.0),
            key=lambda c: (-float(c["denseScore"]), str(c["path"])),
        )
        fused = rrf_scores(
            [
                [str(c["path"]) for c in keyword_leg],
                [str(c["path"]) for c in dense_leg],
            ],
            k=RRF_K,
        )
        for cand in candidates:
            cand["stage1Score"] = fused.get(str(cand["path"]), 0.0)
        renorm_pool = True

    candidates.sort(key=lambda c: (-float(c["stage1Score"]), str(c["path"])))

    pool_size = max(max_results * POOL_MULTIPLIER, POOL_FLOOR)
    pool = candidates[:pool_size]

    # Stage 2: re-rank the pool with the learned MemRL utility signal. RRF
    # scores live on a ~1/k scale, so they are z-normalized within the pool
    # first to keep LAMBDA_UTILITY calibrated.
    stage1 = [float(c["stage1Score"]) for c in pool]
    if renorm_pool:
        stage1 = z_norm(stage1)
    z_util = z_norm([float(c["utility"]) for c in pool])
    for i, cand in enumerate(pool):
        cand["score"] = round_val(stage1[i] + LAMBDA_UTILITY * z_util[i], 4)
        cand.pop("stage1Score", None)
    pool.sort(key=lambda c: float(c["score"]), reverse=True)

    return pool[:max_results]
