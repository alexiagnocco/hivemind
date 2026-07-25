"""Tests for Reciprocal Rank Fusion (Phase 3.1).

Covers the rrf_scores primitive (k=60 math, full outer join), the RRF hybrid
retrieval path, and znorm-parity: fusion="znorm" must reproduce the pre-RRF
score-level fusion exactly.
"""

from __future__ import annotations

import pytest

from hivemind.scoring.relevance import (
    LAMBDA_UTILITY,
    RRF_K,
    rrf_scores,
    z_norm,
)
from hivemind.scoring.retrieve import retrieve


class TestRrfScores:
    def test_k60_math_hand_computed(self) -> None:
        fused = rrf_scores([["a", "b", "c"], ["b", "d"]])
        assert fused["a"] == pytest.approx(1 / 61)
        assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
        assert fused["c"] == pytest.approx(1 / 63)
        assert fused["d"] == pytest.approx(1 / 62)

    def test_default_k_is_60(self) -> None:
        assert RRF_K == 60
        assert rrf_scores([["x"]])["x"] == pytest.approx(1 / 61)

    def test_custom_k(self) -> None:
        fused = rrf_scores([["a", "b"]], k=10)
        assert fused["a"] == pytest.approx(1 / 11)
        assert fused["b"] == pytest.approx(1 / 12)

    def test_full_outer_join(self) -> None:
        # IDs unique to either list survive with their single-leg contribution.
        fused = rrf_scores([["only-left"], ["only-right"]])
        assert set(fused) == {"only-left", "only-right"}
        assert fused["only-left"] == fused["only-right"] == pytest.approx(1 / 61)

    def test_agreement_beats_single_leg_top(self) -> None:
        # A mid-ranked ID in both lists outscores a top-ranked ID in one list.
        fused = rrf_scores([["a", "both"], ["b", "both"]])
        assert fused["both"] > fused["a"]
        assert fused["both"] > fused["b"]

    def test_empty_inputs(self) -> None:
        assert rrf_scores([]) == {}
        assert rrf_scores([[], []]) == {}

    def test_duplicate_within_list_counts_best_rank_only(self) -> None:
        fused = rrf_scores([["a", "a", "b"]])
        assert fused["a"] == pytest.approx(1 / 61)
        assert fused["b"] == pytest.approx(1 / 63)


@pytest.fixture
def corpus(make_note):
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


class TestRrfHybridPath:
    def test_zero_keyword_note_recovered_by_dense_leg(self, corpus) -> None:
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],  # ms == 0, dense 1.0
            "sql-notes.md": [0.0, 0.0, 1.0, 0.0],  # dense 0 → dropped
        }
        top, _rid, _gaps = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector, fusion="rrf",
        )
        paths = [r["path"] for r in top]
        assert "version-control.md" in paths
        assert "git-guide.md" in paths
        assert "sql-notes.md" not in paths

    def test_both_legs_ranks_first(self, corpus) -> None:
        # git-guide matches the keyword leg AND ranks in the dense leg, so its
        # outer-join sum beats the dense-only note.
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],
        }
        top, _rid, _gaps = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector, fusion="rrf",
        )
        assert top[0]["path"] == "git-guide.md"
        # Hand-check the stage-1 RRF ordering: keyword leg = [git-guide],
        # dense leg = [version-control, git-guide].
        # git-guide: 1/61 + 1/62 > version-control: 1/61.
        assert top[1]["path"] == "version-control.md"

    def test_default_fusion_is_rrf(self, corpus) -> None:
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],
            "sql-notes.md": [0.0, 0.0, 1.0, 0.0],
        }
        default_top, _r, _g = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector,
        )
        rrf_top, _r, _g = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector, fusion="rrf",
        )
        assert [r["path"] for r in default_top] == [r["path"] for r in rrf_top]
        assert [r["score"] for r in default_top] == [r["score"] for r in rrf_top]

    def test_keyword_only_path_ignores_fusion(self, corpus) -> None:
        for fusion in ("rrf", "znorm"):
            top, _rid, _gaps = retrieve(corpus, {}, query="git", fusion=fusion)
            assert [r["path"] for r in top] == ["git-guide.md"]
            assert all(r["mode"] == "keyword" for r in top)


class TestFusionEdgeCases:
    """Mandated Phase 3 fusion edge cases: empty dense leg, single-note vault,
    all-equal scores (tie-break determinism)."""

    def test_empty_dense_leg_keeps_keyword_ranking(self, corpus) -> None:
        # Query vector orthogonal to every note vector → the dense leg is
        # empty; keyword matches must survive on their leg alone.
        query_vector = [0.0, 0.0, 0.0, 1.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],
            "sql-notes.md": [0.0, 0.0, 1.0, 0.0],
        }
        for fusion in ("rrf", "znorm"):
            top, _rid, _gaps = retrieve(
                corpus, {}, query="git", max_results=10,
                note_vectors=note_vectors, query_vector=query_vector, fusion=fusion,
            )
            assert [r["path"] for r in top] == ["git-guide.md"], fusion

    def test_single_note_vault(self, make_note) -> None:
        note = make_note("solo.md", title="Git guide", summary="rebase", inbound=1)
        for fusion in ("rrf", "znorm"):
            top, _rid, _gaps = retrieve(
                [note], {}, query="git", max_results=5,
                note_vectors={"solo.md": [1.0, 0.0]}, query_vector=[1.0, 0.0],
                fusion=fusion,
            )
            assert [r["path"] for r in top] == ["solo.md"], fusion
            # Degenerate z-norm (variance 0) collapses to 0.0, never NaN/inf.
            assert top[0]["score"] == 0.0, fusion

    def test_all_equal_scores_break_ties_by_path_deterministically(
        self, make_note
    ) -> None:
        def notes():
            return [
                make_note(p, title="Git notes", summary="rebase workflow", inbound=2)
                for p in ("zc.md", "za.md", "zb.md")  # deliberately unsorted
            ]

        vec = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {p: vec for p in ("za.md", "zb.md", "zc.md")}
        for fusion in ("rrf", "znorm"):
            runs = [
                [
                    r["path"]
                    for r in retrieve(
                        notes(), {}, query="git", max_results=10,
                        note_vectors=note_vectors, query_vector=vec, fusion=fusion,
                    )[0]
                ]
                for _ in range(2)
            ]
            assert runs[0] == runs[1] == ["za.md", "zb.md", "zc.md"], fusion

    def test_keyword_path_ties_break_by_path(self, make_note) -> None:
        # Regression: the keyword-only path relied on manifest order for
        # ties; it must tie-break by path like the hybrid and chunk paths.
        notes = [
            make_note(p, title="Git notes", summary="rebase workflow", inbound=2)
            for p in ("zc.md", "za.md", "zb.md")
        ]
        top, _rid, _gaps = retrieve(notes, {}, query="git", max_results=10)
        assert [r["path"] for r in top] == ["za.md", "zb.md", "zc.md"]


class TestChunkFusionEdgeCases:
    """The same edge cases on the chunk-granularity fusion path."""

    @staticmethod
    def _index(*paths: str):
        from hivemind.state.chunk_store import ChunkRecord

        return {
            p: [
                ChunkRecord(
                    path=p, anchor="A", section="A",
                    text="git rebase workflow notes", embed_hash=f"h-{p}",
                )
            ]
            for p in paths
        }

    def test_empty_dense_leg_keyword_only_is_deterministic(self, make_note) -> None:
        from hivemind.scoring.retrieve import retrieve_chunks

        notes = [make_note("b.md", title="B"), make_note("a.md", title="A")]
        for fusion in ("rrf", "znorm"):
            results, _rid, gaps = retrieve_chunks(
                notes, {}, self._index("a.md", "b.md"),
                query="git rebase", fusion=fusion,
            )
            # Equal keyword scores, no dense leg → ties break by chunk id.
            assert [r["path"] for r in results] == ["a.md", "b.md"], fusion
            assert gaps == []

    def test_all_chunkless_notes_return_gap(self, make_note) -> None:
        from hivemind.scoring.retrieve import retrieve_chunks

        # Frontmatter-only notes chunk to an empty list — no candidates.
        results, _rid, gaps = retrieve_chunks(
            [make_note("a.md", title="A")], {}, {"a.md": []}, query="git",
        )
        assert results == []
        assert gaps == ["No vault content found for 'git'"]

    def test_single_chunk_hive_degenerate_znorm(self, make_note) -> None:
        from hivemind.scoring.retrieve import retrieve_chunks

        for fusion in ("rrf", "znorm"):
            results, _rid, _gaps = retrieve_chunks(
                [make_note("a.md", title="A")], {}, self._index("a.md"),
                query="rebase", fusion=fusion,
            )
            assert len(results) == 1, fusion
            assert results[0]["score"] == 0.0, fusion


class TestZnormParity:
    """fusion="znorm" must reproduce the pre-RRF hybrid scoring exactly."""

    def _expected_znorm(self, cands, dense_weight=1.0):
        """Reference implementation of the pre-change fusion math."""
        z_base = z_norm([c["base"] for c in cands])
        z_dense = z_norm([c["dense"] for c in cands])
        stage1 = [z_base[i] + dense_weight * z_dense[i] for i in range(len(cands))]
        order = sorted(range(len(cands)), key=lambda i: -stage1[i])
        z_util = z_norm([cands[i]["util"] for i in order])
        scored = {
            cands[i]["path"]: stage1[i] + LAMBDA_UTILITY * z_util[j]
            for j, i in enumerate(order)
        }
        return dict(sorted(scored.items(), key=lambda kv: -kv[1]))

    def test_znorm_scores_match_reference_math(self, corpus) -> None:
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],
            "sql-notes.md": [0.1, 0.0, 0.9, 0.0],
        }
        top, _rid, _gaps = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector, fusion="znorm",
        )
        cands = [
            {"path": r["path"], "base": float(r["baseScore"]),
             "dense": float(r["denseScore"]), "util": float(r["utility"])}
            for r in sorted(top, key=lambda r: r["path"])
        ]
        expected = self._expected_znorm(cands)
        assert [r["path"] for r in top] == list(expected)
        for r in top:
            assert r["score"] == pytest.approx(expected[r["path"]], abs=1e-4)

    def test_znorm_preserves_test_retrieve_expectations(self, corpus) -> None:
        # The headline expectations from tests/test_retrieve.py::TestHybrid,
        # re-run explicitly under the retained znorm strategy.
        query_vector = [1.0, 0.0, 0.0, 0.0]
        note_vectors = {
            "git-guide.md": [0.6, 0.4, 0.0, 0.0],
            "version-control.md": [1.0, 0.0, 0.0, 0.0],
            "sql-notes.md": [0.0, 0.0, 1.0, 0.0],
        }
        top, _rid, _gaps = retrieve(
            corpus, {}, query="git", max_results=10,
            note_vectors=note_vectors, query_vector=query_vector, fusion="znorm",
        )
        paths = [r["path"] for r in top]
        assert "version-control.md" in paths
        assert "git-guide.md" in paths
        assert "sql-notes.md" not in paths
        assert all(r["mode"] == "hybrid" for r in top)
