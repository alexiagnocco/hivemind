"""Tests for the REST client header-encoding fix (non-ASCII / em-dash bug).

Before the fix, ``_safe_header`` only stripped CRLF, so a heading containing an
em-dash (U+2014) raised ``UnicodeEncodeError`` inside httpx (headers must be
Latin-1 encodable). The fix percent-encodes the ``Target`` and
``Apply-If-Content-Preexists`` headers, which the Obsidian REST API URL-decodes.
"""

from __future__ import annotations

from urllib.parse import unquote

import httpx
import respx

from hivemind.config import Settings
from hivemind.rest.client import (
    ObsidianRestClient,
    _encode_header,
    _safe_header,
)

EM_DASH = "—"


class TestEncodeHeader:
    def test_em_dash_becomes_ascii(self) -> None:
        encoded = _encode_header(f"Summary {EM_DASH} Q1")
        assert encoded.isascii()
        assert EM_DASH not in encoded

    def test_round_trips_via_url_decode(self) -> None:
        original = f"Decisions {EM_DASH} 2026 / scope"
        assert unquote(_encode_header(original)) == original

    def test_strips_crlf(self) -> None:
        encoded = _encode_header("a\r\nInjected: header")
        assert "\r" not in encoded
        assert "\n" not in encoded

    def test_plain_ascii_round_trips(self) -> None:
        assert unquote(_encode_header("Session Checkpoints")) == "Session Checkpoints"


class TestSafeHeader:
    def test_strips_crlf(self) -> None:
        assert _safe_header("append\r\nX: y") == "appendX: y"

    def test_ascii_enum_unchanged(self) -> None:
        assert _safe_header("heading") == "heading"
        assert _safe_header("::") == "::"


def _client() -> ObsidianRestClient:
    settings = Settings(obsidian_api_key="test-key", obsidian_rest_url="https://x")
    return ObsidianRestClient(settings)


@respx.mock
async def test_patch_note_with_em_dash_target_does_not_raise() -> None:
    route = respx.patch("https://x/vault/note.md").mock(
        return_value=httpx.Response(200)
    )
    client = _client()
    try:
        target = f"Summary {EM_DASH} Q1"
        await client.patch_note(
            "note.md", "body", target_type="heading", target=target, operation="append"
        )
    finally:
        await client.aclose()

    sent = route.calls.last.request
    assert sent.headers["Target"].isascii()
    assert unquote(sent.headers["Target"]) == target
    # ASCII control headers are sent verbatim.
    assert sent.headers["Target-Type"] == "heading"
    assert sent.headers["Operation"] == "append"


@respx.mock
async def test_patch_note_encodes_apply_if_content_preexists() -> None:
    route = respx.patch("https://x/vault/n.md").mock(return_value=httpx.Response(200))
    client = _client()
    guard = f"already {EM_DASH} written"
    try:
        await client.patch_note(
            "n.md", "body", target_type="heading", target="H",
            operation="append", apply_if_content_preexists=guard,
        )
    finally:
        await client.aclose()

    sent = route.calls.last.request
    assert sent.headers["Apply-If-Content-Preexists"].isascii()
    assert unquote(sent.headers["Apply-If-Content-Preexists"]) == guard


@respx.mock
async def test_nested_heading_target_round_trips() -> None:
    route = respx.patch("https://x/vault/n.md").mock(return_value=httpx.Response(200))
    client = _client()
    try:
        await client.patch_note(
            "n.md", "body", target_type="heading",
            target="Parent::Child", operation="append",
        )
    finally:
        await client.aclose()

    sent = route.calls.last.request
    # Server decodes Target first, then splits on the (verbatim) delimiter.
    assert unquote(sent.headers["Target"]) == "Parent::Child"
    assert sent.headers["Target-Delimiter"] == "::"


def test_settings_does_not_raise_without_keyring() -> None:
    # Constructing settings with an explicit key must not depend on keyring.
    s = Settings(obsidian_api_key="k")
    assert s.obsidian_api_key == "k"
