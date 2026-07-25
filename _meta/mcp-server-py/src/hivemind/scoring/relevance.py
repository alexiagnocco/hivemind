"""Verbatim port of helpers.ts scoring functions (lines 156-272, 225-233, 329-344)."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hivemind.model.note import Note
    from hivemind.state.utility import UtilityScores

ALPHA = 0.3
LAMBDA_UTILITY = 0.5

# Reciprocal Rank Fusion: rank-list smoothing constant. k=60 is the standard
# value from Cormack et al.; larger k flattens the contribution curve.
RRF_K = 60

# Hybrid retrieval: weight of the z-normalized dense (cosine) signal relative to
# the z-normalized keyword composite in stage-1 fusion. 1.0 puts dense on equal
# footing with the keyword base score.
W_DENSE = 1.0
# Stage-1 candidate pool size is max(max_results * POOL_MULTIPLIER, POOL_FLOOR);
# only this pool is carried into the stage-2 utility (MemRL) re-rank.
POOL_MULTIPLIER = 5
POOL_FLOOR = 25


def freshness_score(updated: str) -> int:
    try:
        updated_date = datetime.strptime(updated[:10], "%Y-%m-%d").replace(tzinfo=UTC)
        days = (datetime.now(UTC) - updated_date).days
        if days <= 1:
            return 5
        if days <= 7:
            return 4
        if days <= 14:
            return 3
        if days <= 30:
            return 2
        if days <= 90:
            return 1
        return 0
    except (ValueError, TypeError):
        return 0


def connectivity_score(note: Note) -> int:
    return min(note.inboundCount, 5)


def match_score(note: Note, query: str, project: str) -> int:
    score = 0
    p = project.lower()
    title = (note.title or "").lower()
    basename_val = (note.basename or "").lower()
    summary = (note.summary or "").lower()
    preview = (note.preview or "").lower()
    tags = " ".join(note.tags).lower()
    searchable = f"{title} {basename_val} {summary} {preview} {tags}"

    if p:
        if p in basename_val:
            score += 5
        if p in searchable:
            score += 3

    if query:
        q = query.lower()
        if q in basename_val:
            score += 4
        elif q in title:
            score += 3
        elif q in searchable:
            score += 2
        else:
            words = [w for w in q.split() if len(w) > 1]
            if words:
                matched = 0
                word_score = 0
                for word in words:
                    if word in basename_val:
                        matched += 1
                        word_score += 3
                    elif word in title:
                        matched += 1
                        word_score += 2
                    elif word in searchable:
                        matched += 1
                        word_score += 1
                if matched >= math.ceil(len(words) / 2):
                    score += word_score

    if not query and not p:
        score = 1
    return score


def utility_score(path: str, scores: UtilityScores) -> float:
    entry = scores.get(path)
    if entry is None:
        return 0.5
    return entry.utility


def rrf_scores(rank_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion over ranked ID lists (full outer join).

    Every ID appearing in *any* list gets a score; each list contributes
    ``1 / (k + rank)`` with 1-based ranks, and lists that omit an ID simply
    contribute nothing for it. Duplicate IDs within one list count only at
    their best (first) rank.
    """
    fused: dict[str, float] = {}
    for ranks in rank_lists:
        seen: set[str] = set()
        for idx, item in enumerate(ranks):
            if item in seen:
                continue
            seen.add(item)
            fused[item] = fused.get(item, 0.0) + 1.0 / (k + idx + 1)
    return fused


def z_norm(values: list[float]) -> list[float]:
    if not values:
        return []
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    if variance < 1e-10:
        return [0.0] * n
    std = math.sqrt(variance)
    return [(v - mean) / std for v in values]


def match_note(
    note: Note,
    *,
    query: str = "",
    domain: str = "",
    tags: list[str] | None = None,
    note_type: str = "",
    status: str = "",
    project: str = "",
) -> bool:
    if domain and (note.domain or "") != domain:
        return False
    if note_type and (note.type or "") != note_type:
        return False
    if status and (note.status or "") != status:
        return False
    if project and (note.project or "") != project:
        return False
    if tags:
        note_tags = set(note.tags)
        if not all(t in note_tags for t in tags):
            return False
    if query:
        q = query.lower()
        searchable = " ".join([
            note.title or "",
            note.summary or "",
            note.path or "",
            note.basename or "",
            *note.tags,
        ]).lower()
        if q not in searchable:
            words = [w for w in q.split() if len(w) > 1]
            if not words or not all(w in searchable for w in words):
                return False
    return True


def retrieval_id() -> str:
    d = datetime.now()
    return (
        f"{d.year:04d}{d.month:02d}{d.day:02d}"
        f"{d.hour:02d}{d.minute:02d}{d.second:02d}"
    )


def round_val(n: float, decimals: int) -> float:
    f = 10**decimals
    return float(round(n * f) / f)
