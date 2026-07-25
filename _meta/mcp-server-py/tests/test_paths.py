"""Tests for fs.paths.is_system_note — the content/system classification.

Covers the repo-surface extension (.github/** + root README.md), regression
for the pre-existing rules ported from helpers.ts, and the two contracts the
extension must honor: system notes disappear from health orphan/content
counts but remain fully retrievable.
"""

from __future__ import annotations

import pytest

from hivemind.fs.paths import is_system_note
from hivemind.scoring.health import compute_health
from hivemind.scoring.retrieve import retrieve


class TestRepoSurfaceClassification:
    """The 2026-07-11 extension: Copilot-surface files and the repo README
    are system notes — indexed and retrievable, never content/orphans."""

    @pytest.mark.parametrize("path", [
        ".github/agents/hivemind.agent.md",
        ".github/agents/hivemind-librarian.agent.md",
        ".github/copilot-instructions.md",
        ".github/instructions/hivemind-server.instructions.md",
        ".github/instructions/vault-notes.instructions.md",
        ".github/prompts/boot.prompt.md",
        ".github/prompts/wrap.prompt.md",
    ])
    def test_github_surface_files_are_system(self, path: str) -> None:
        assert is_system_note(path)

    def test_root_readme_is_system(self) -> None:
        assert is_system_note("README.md")

    def test_nested_readme_in_content_dir_is_not_system(self) -> None:
        # Only the repo-root README is repo surface; a README filed inside a
        # content folder is an ordinary note.
        assert not is_system_note("30-resources/backend/README.md")

    def test_github_prefix_requires_directory(self) -> None:
        # A note merely named after .github must not be swept up.
        assert not is_system_note("30-resources/git/github-actions-notes.md")


class TestExistingRulesRegression:
    """The rules ported from helpers.ts must be unaffected by the extension."""

    @pytest.mark.parametrize("path", [
        "40-archive/10-projects/old-project/note.md",
        "_templates/note-template.md",
        "_meta/inbox/2026-07-01-triage.md",
        "_meta/mcp-server-py/README.md",
        "_meta/scripts/rebuild.md",
        "_meta/_archive/old.md",
        "_meta/hive-health.md",
        ".claude/skills/boot/references/deep-dive.md",
        ".claude/skills/boot/SKILL.md",
        "memory/feedback_retrieval.md",
        "memory/reference_dates.md",
        "10-projects/_README.md",
        "_README.md",
        "CLAUDE.md",
        "CREDITS.md",
        "EXAMPLES.md",
        "STRUCTURE.md",
        "LICENSE.md",
        "memory/MEMORY.md",
    ])
    def test_system_paths(self, path: str) -> None:
        assert is_system_note(path)

    @pytest.mark.parametrize("path", [
        "10-projects/hivemind/ADR-001-stable-dimension-subdirectory-taxonomy.md",
        "20-areas/reliability/error-budgets.md",
        "30-resources/backend/auth-token-expiry-bug.md",
        "50-maps/MOC-Projects.md",
        "memory/projects/hivemind.md",
        "memory/glossary.md",
        "00-inbox/raw-capture.md",
        "docs/STRUCTURE.md",
        "specs/copilot-optimization-plan.md",
    ])
    def test_content_paths(self, path: str) -> None:
        assert not is_system_note(path)


class TestHealthCountsExcludeRepoSurface:
    """compute_health must count .github/** + root README.md as K_system,
    not as content notes or actionable orphans."""

    @pytest.fixture
    def corpus(self, make_note):
        return [
            # Content: one linked, one orphan.
            make_note("30-resources/backend/linked.md", inbound=2),
            make_note("30-resources/backend/genuine-orphan.md", inbound=0),
            # Repo surface: zero inbound wikilinks, must not count as orphans.
            make_note(".github/agents/hivemind.agent.md", inbound=0),
            make_note(".github/prompts/boot.prompt.md", inbound=0),
            make_note("README.md", inbound=0),
        ]

    def test_content_and_orphan_counts(self, corpus) -> None:
        health = compute_health(corpus, [], {})
        assert health["K"] == 5
        assert health["K_content"] == 2
        assert health["K_system"] == 3
        assert health["sigma_orphans_actionable"] == 1  # genuine-orphan.md only
        assert health["sigma_orphans_total"] == 4

    def test_sigma_denominator_is_content_only(self, corpus) -> None:
        health = compute_health(corpus, [], {})
        # 1 linked of 2 content notes — the three system notes don't dilute.
        assert health["sigma_proxy"] == pytest.approx(0.5)


class TestRepoSurfaceStaysRetrievable:
    """Zero behavior change for retrieval: system classification must not
    gate the scoring path (only 40-archive/ is filtered there)."""

    def test_github_agent_note_retrievable_by_keyword(self, make_note) -> None:
        notes = [
            make_note(
                ".github/agents/hivemind.agent.md",
                title="Hivemind vault retrieval agent",
                summary="copilot agent for vault retrieval",
                inbound=0,
            ),
            make_note("30-resources/backend/unrelated.md", title="SQL notes"),
        ]
        top, _rid, _gaps = retrieve(notes, {}, query="copilot agent", max_results=5)
        assert ".github/agents/hivemind.agent.md" in [r["path"] for r in top]

    def test_root_readme_retrievable_by_keyword(self, make_note) -> None:
        notes = [
            make_note("README.md", title="Install the MCP server",
                      summary="installation quickstart"),
        ]
        top, _rid, _gaps = retrieve(notes, {}, query="install quickstart", max_results=5)
        assert [r["path"] for r in top] == ["README.md"]
