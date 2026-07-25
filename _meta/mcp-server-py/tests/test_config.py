"""Tests for Settings vault-root resolution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from hivemind.config import Settings, _detect_hive_root

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_detect_hive_root_finds_enclosing_vault() -> None:
    # This source tree IS a vault: config.py lives under <root>/_meta/mcp-server-py.
    assert _detect_hive_root() == REPO_ROOT


def test_settings_default_hive_path_is_detected_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HIVE_PATH", raising=False)
    settings = Settings(_env_file=None)
    assert settings.hive_path == REPO_ROOT


def test_env_var_overrides_detection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HIVE_PATH", str(tmp_path))
    settings = Settings(_env_file=None)
    assert settings.hive_path == tmp_path.resolve()
