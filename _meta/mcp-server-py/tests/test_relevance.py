"""Unit tests for the pure scoring functions (the retrieval core)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hivemind.scoring.relevance import (
    connectivity_score,
    freshness_score,
    match_note,
    match_score,
    round_val,
    z_norm,
)


def _days_ago(n: int) -> str:
    return (datetime.now(UTC) - timedelta(days=n)).strftime("%Y-%m-%d")


class TestFreshnessScore:
    def test_buckets(self) -> None:
        assert freshness_score(_days_ago(0)) == 5
        assert freshness_score(_days_ago(5)) == 4
        assert freshness_score(_days_ago(10)) == 3
        assert freshness_score(_days_ago(20)) == 2
        assert freshness_score(_days_ago(60)) == 1
        assert freshness_score(_days_ago(200)) == 0

    def test_invalid_returns_zero(self) -> None:
        assert freshness_score("") == 0
        assert freshness_score("not-a-date") == 0


class TestConnectivityScore:
    def test_caps_at_five(self, make_note) -> None:
        assert connectivity_score(make_note("a.md", inbound=0)) == 0
        assert connectivity_score(make_note("a.md", inbound=3)) == 3
        assert connectivity_score(make_note("a.md", inbound=99)) == 5


class TestMatchScore:
    def test_basename_match_strongest(self, make_note) -> None:
        note = make_note("git-guide.md", title="Git Guide", summary="about git")
        assert match_score(note, "git-guide", "") == 4

    def test_title_match(self, make_note) -> None:
        note = make_note("g.md", title="Rebase Workflow", summary="x")
        assert match_score(note, "rebase workflow", "") == 3

    def test_searchable_match(self, make_note) -> None:
        note = make_note("g.md", title="Workflow", summary="discusses rebasing topics")
        assert match_score(note, "rebasing topics", "") == 2

    def test_no_query_no_project_is_one(self, make_note) -> None:
        assert match_score(make_note("g.md", title="x"), "", "") == 1

    def test_zero_when_no_overlap(self, make_note) -> None:
        note = make_note("sql.md", title="SQL Functions", summary="query patterns")
        assert match_score(note, "kubernetes", "") == 0

    def test_multiword_threshold(self, make_note) -> None:
        # Half-or-more of the words must hit for the multi-word branch to score.
        note = make_note("g.md", title="alpha beta", summary="")
        assert match_score(note, "alpha zzzz", "") > 0  # 1 of 2 hits (ceil(2/2)=1)
        assert match_score(note, "alpha yyyy zzzz wwww", "") == 0  # 1 of 4 < ceil(4/2)


class TestZNorm:
    def test_empty(self) -> None:
        assert z_norm([]) == []

    def test_zero_variance(self) -> None:
        assert z_norm([3.0, 3.0, 3.0]) == [0.0, 0.0, 0.0]

    def test_standardizes(self) -> None:
        out = z_norm([1.0, 2.0, 3.0])
        assert abs(sum(out)) < 1e-9
        assert out[0] < 0 < out[2]


class TestMatchNote:
    def test_domain_filter(self, make_note) -> None:
        note = make_note("a.md", domain="work")
        assert match_note(note, domain="work")
        assert not match_note(note, domain="ops")

    def test_tags_all_required(self, make_note) -> None:
        note = make_note("a.md", tags=["git", "sql"])
        assert match_note(note, tags=["git"])
        assert not match_note(note, tags=["git", "python"])


def test_round_val() -> None:
    assert round_val(1.23456, 3) == 1.235
    assert round_val(2.0, 2) == 2.0
