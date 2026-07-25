"""Tests for the hybrid retrieval scorer.

Covers (a) backward-compatible keyword-only behavior and (b) the headline fix:
a conceptually relevant note with no keyword overlap, which the keyword path
drops, now surfaces on the hybrid path.
"""

from __future__ import annotations

import pytest

from hivemind.scoring.retrieve import retrieve


@pytest.fixture
def corpus(make_note):
    # n_kw: matches the keyword "git". n_sem: about version control but contains
    # no "git" token anywhere. n_off: unrelated.
    return [
        make_note("git-guide.md", title="Git rebase guide", summary="how to rebase", inbound=2),
        make_note(
            "version-control.md",
            title="Source history and branching philosophy",
            summary="managing change over time in a repository",
            inbound=2,
        ),
        make_note("sql-notes.md", title="SQL notes", summary="query patterns", inbound=2),
    ]


class TestKeywordOnly:
    def test_zero_keyword_note_is_dropped(self, corpus) -> None:
        top, _rid, _gaps = retrieve(corpus, {}, query="git", max_results=10)
        paths = [r["path"] for r in top]
        assert "git-guide.md" in paths
        assert "version-control.md" not in paths  # ms == 0 → dropped (legacy behavior)
        assert "sql-notes.md" not in paths

    def test_results_carry_keyword_mode(self, corpus) -> None:
        top, _rid, _gaps = retrieve(corpus, {}, query="git", max_results=10)
        assert all(r["mode"] == "keyword" for r in top)
        assert all(r["denseScore"] == 0.0 for r in top)

    def test_gap_when_no_match(self, corpus) -> None:
        top, _rid, gaps = retrieve(corpus, {}, query="kubernetes", max_results=10)
        assert top == []
        assert any("kubernetes" in g for g in gaps)

    def test_browse_includes_all_nonarchived(self, corpus) -> None:
        top, _rid, _gaps = retrieve(corpus, {}, query="", max_results=10)
        assert len(top) == 3


class TestHybrid:
    def test_zero_keyword_but_semantically_relevant_surfaces(self, corpus) -> None:
        # query_vector aligns with version-control.md, which has NO "git" keyword.
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],  # cosine 1.0, ms == 0
            "sql-notes.md": [0.0, 0.0, 1.0, 0.0],  # cosine 0 → dropped
        }
        top, _rid, _gaps = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector,
        )
        paths = [r["path"] for r in top]
        # The whole point: the no-keyword note is recovered by dense similarity.
        assert "version-control.md" in paths
        assert "git-guide.md" in paths
        # Orthogonal, non-matching note stays out.
        assert "sql-notes.md" not in paths
        assert all(r["mode"] == "hybrid" for r in top)

    def test_dense_score_recorded(self, corpus) -> None:
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {"version-control.md": [1.0, 0.0, 0.0, 0.0]}
        top, _rid, _gaps = retrieve(
            corpus, {}, query="anything", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector,
        )
        vc = next(r for r in top if r["path"] == "version-control.md")
        assert vc["denseScore"] == pytest.approx(1.0, abs=1e-6)

    def test_max_results_respected(self, corpus) -> None:
        query_vector = [1.0, 0.0, 0.0]
        note_vectors = {n.path: [1.0, 0.0, 0.0] for n in corpus}
        top, _rid, _gaps = retrieve(
            corpus, {}, query="x", max_results=2,
            note_vectors=note_vectors, query_vector=query_vector,
        )
        assert len(top) == 2

    def test_archived_excluded_by_default(self, make_note) -> None:
        notes = [
            make_note("40-archive/old.md", title="archived git note", inbound=1),
            make_note("git-guide.md", title="Git guide", inbound=1),
        ]
        qv = [1.0, 0.0]
        nv = {"40-archive/old.md": [1.0, 0.0], "git-guide.md": [1.0, 0.0]}
        top, _rid, _gaps = retrieve(
            notes, {}, query="git", max_results=10, note_vectors=nv, query_vector=qv,
        )
        assert "40-archive/old.md" not in [r["path"] for r in top]

    def test_domain_filter(self, make_note) -> None:
        notes = [
            make_note("a.md", title="git a", domain="work", inbound=1),
            make_note("b.md", title="git b", domain="ops", inbound=1),
        ]
        qv = [1.0, 0.0]
        nv = {"a.md": [1.0, 0.0], "b.md": [1.0, 0.0]}
        top, _rid, _gaps = retrieve(
            notes, {}, query="git", domain="work", max_results=10,
            note_vectors=nv, query_vector=qv,
        )
        assert [r["path"] for r in top] == ["a.md"]
