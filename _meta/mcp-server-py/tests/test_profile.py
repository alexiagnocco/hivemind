"""Profile-conditional tool registration (HIVEMIND_PROFILE).

FastMCP registration happens at import time (@mcp.tool decorators), so each
profile is exercised in a fresh subprocess interpreter — an in-process reload
would leak the first import's registrations.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

LEAN_TOOLS = {
    "hive_retrieve",
    "hive_search",
    "hive_read",
    "hive_context",
    "hive_related",
    "hive_feedback",
    "hive_rebuild",
    "hive_status",
}
FULL_TOOL_COUNT = 23

_SCRIPT = (
    "import asyncio, json\n"
    "from hivemind.server import mcp\n"
    "print(json.dumps(sorted(t.name for t in asyncio.run(mcp.list_tools()))))\n"
)


def _registered_tools(profile: str | None) -> set[str]:
    env = os.environ.copy()
    env.pop("HIVEMIND_PROFILE", None)
    if profile is not None:
        env["HIVEMIND_PROFILE"] = profile
    proc = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return set(json.loads(proc.stdout.strip().splitlines()[-1]))


def test_lean_registers_exactly_the_eight_core_tools() -> None:
    assert _registered_tools("lean") == LEAN_TOOLS


def test_full_registers_all_tools() -> None:
    tools = _registered_tools("full")
    assert len(tools) == FULL_TOOL_COUNT
    assert tools >= LEAN_TOOLS


def test_default_profile_is_full() -> None:
    assert len(_registered_tools(None)) == FULL_TOOL_COUNT


def test_unknown_profile_falls_back_to_full() -> None:
    assert len(_registered_tools("bogus")) == FULL_TOOL_COUNT


def test_uppercase_profile_is_normalized() -> None:
    assert _registered_tools(" LEAN ") == LEAN_TOOLS


_SETTINGS_SCRIPT = (
    "from hivemind.server import mcp\n"
    "from hivemind.config import Settings\n"
    "print(Settings(obsidian_api_key='k').hivemind_profile)\n"
)


def _settings_profile(profile: str) -> str:
    env = os.environ.copy()
    env["HIVEMIND_PROFILE"] = profile
    proc = subprocess.run(
        [sys.executable, "-c", _SETTINGS_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return proc.stdout.strip().splitlines()[-1]


@pytest.mark.parametrize("profile", ["bogus", "LEAN", "lean", "full"])
def test_settings_profile_agrees_with_registration(profile: str) -> None:
    # Regression: an invalid HIVEMIND_PROFILE used to pass server.py's
    # graceful fallback but crash Settings() (strict Literal) at lifespan
    # startup, killing the server. Settings must always resolve to the same
    # profile the server registered.
    expected = profile.strip().lower()
    if expected not in ("full", "lean"):
        expected = "full"
    assert _settings_profile(profile) == expected
