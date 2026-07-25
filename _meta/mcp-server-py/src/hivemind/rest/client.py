from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from hivemind.rest.errors import (
    AuthenticationError,
    PluginUnavailableError,
    PluginVersionError,
)
from hivemind.rest.tls import build_tls_verify

if TYPE_CHECKING:
    from hivemind.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusResponse:
    authenticated: bool
    service: str
    plugin_version: str
    obsidian_version: str
    raw: dict[str, Any]


class ObsidianRestClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        tls_verify = build_tls_verify(settings.tls_verify)
        self._http = httpx.AsyncClient(
            base_url=settings.obsidian_rest_url,
            headers={"Authorization": f"Bearer {settings.obsidian_api_key}"},
            verify=tls_verify,
            timeout=httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0),
        )

    async def ping(self) -> StatusResponse:
        try:
            resp = await self._http.get("/")
        except httpx.ConnectError as exc:
            raise PluginUnavailableError("Connection refused") from exc
        except httpx.TimeoutException as exc:
            raise PluginUnavailableError("Connection timeout") from exc

        if resp.status_code == 401:
            raise AuthenticationError("Invalid or expired API key (401)")

        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

        versions: dict[str, str] = data.get("versions", {})
        plugin_ver = versions.get("self", "unknown")

        min_ver = self._settings.obsidian_rest_api_version_min
        if plugin_ver != "unknown" and _version_lt(plugin_ver, min_ver):
            raise PluginVersionError(f"Plugin {plugin_ver} below minimum {min_ver}")

        return StatusResponse(
            authenticated=data.get("authenticated", False),
            service=data.get("service", "unknown"),
            plugin_version=plugin_ver,
            obsidian_version=versions.get("obsidian", "unknown"),
            raw=data,
        )

    async def get_note(self, path: str, *, as_json: bool = False) -> dict[str, Any] | str:
        """GET /vault/{path}. Returns markdown string or NoteJson dict."""
        accept = "application/vnd.olrapi.note+json" if as_json else "text/markdown"
        url = f"/vault/{_encode_path(path)}"
        resp = await self._request("GET", url, headers={"Accept": accept})
        if as_json:
            return resp.json()  # type: ignore[no-any-return]
        return resp.text

    async def get_active(self, *, as_json: bool = False) -> dict[str, Any] | str:
        """GET /active/. Returns the currently-open note."""
        accept = "application/vnd.olrapi.note+json" if as_json else "text/markdown"
        resp = await self._request("GET", "/active/", headers={"Accept": accept})
        if as_json:
            return resp.json()  # type: ignore[no-any-return]
        return resp.text

    async def get_document_map(self, path: str) -> dict[str, Any]:
        """GET /vault/{path} with Accept: document-map. Returns heading/block skeleton."""
        resp = await self._request(
            "GET",
            f"/vault/{_encode_path(path)}",
            headers={"Accept": "application/vnd.olrapi.document-map+json"},
        )
        return resp.json()  # type: ignore[no-any-return]

    async def search_simple(
        self, query: str, context_length: int = 100
    ) -> list[dict[str, Any]]:
        """POST /search/simple/?query=... — full-text fuzzy search."""
        from urllib.parse import quote

        url = f"/search/simple/?query={quote(query)}&contextLength={context_length}"
        resp = await self._request("POST", url)
        return resp.json()  # type: ignore[no-any-return]

    async def list_tags(self) -> dict[str, Any]:
        """GET /tags/ — returns {"tags": [{"name": ..., "count": ...}, ...]}."""
        resp = await self._request("GET", "/tags/")
        return resp.json()  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Phase 5 write methods
    # ------------------------------------------------------------------

    async def put_note(self, path: str, content: str) -> httpx.Response:
        """PUT /vault/{path} — create or overwrite a note."""
        return await self._request(
            "PUT",
            f"/vault/{_encode_path(path)}",
            headers={"Content-Type": "text/markdown"},
            content=content,
        )

    async def post_append(self, path: str, content: str) -> httpx.Response:
        """POST /vault/{path} — append to an existing note."""
        return await self._request(
            "POST",
            f"/vault/{_encode_path(path)}",
            headers={"Content-Type": "text/markdown"},
            content=content,
        )

    async def delete_note(self, path: str) -> httpx.Response:
        """DELETE /vault/{path} — delete a note."""
        return await self._request("DELETE", f"/vault/{_encode_path(path)}")

    async def patch_note(
        self,
        path: str,
        content: str,
        *,
        target_type: str,
        target: str,
        target_delimiter: str = "::",
        operation: str = "append",
        create_if_missing: bool = False,
        apply_if_content_preexists: str | None = None,
        content_type: str = "text/markdown",
    ) -> httpx.Response:
        """PATCH /vault/{path} — surgical edit at a heading/block/frontmatter target."""
        headers: dict[str, str] = {
            "Content-Type": content_type,
            "Target-Type": _safe_header(target_type),
            "Target": _encode_header(target),
            "Target-Delimiter": _safe_header(target_delimiter),
            "Operation": _safe_header(operation),
        }
        if create_if_missing:
            headers["Create-Target-If-Missing"] = "true"
        if apply_if_content_preexists is not None:
            headers["Apply-If-Content-Preexists"] = _encode_header(
                apply_if_content_preexists
            )
        return await self._request(
            "PATCH",
            f"/vault/{_encode_path(path)}",
            headers=headers,
            content=content,
        )

    # ------------------------------------------------------------------
    # Phase 6 methods — periodic, commands, open, active write
    # ------------------------------------------------------------------

    async def get_periodic(
        self,
        period: str,
        *,
        date: str = "",
        as_json: bool = False,
    ) -> dict[str, Any] | str:
        """GET /periodic/{period}[/{date}]."""
        url = f"/periodic/{period}/{date}" if date else f"/periodic/{period}"
        accept = "application/vnd.olrapi.note+json" if as_json else "text/markdown"
        resp = await self._request("GET", url, headers={"Accept": accept})
        if as_json:
            return resp.json()  # type: ignore[no-any-return]
        return resp.text

    async def put_periodic(
        self, period: str, content: str, *, date: str = ""
    ) -> httpx.Response:
        """PUT /periodic/{period}[/{date}] — create/overwrite periodic note."""
        url = f"/periodic/{period}/{date}" if date else f"/periodic/{period}"
        return await self._request(
            "PUT", url, headers={"Content-Type": "text/markdown"}, content=content
        )

    async def post_periodic(
        self, period: str, content: str, *, date: str = ""
    ) -> httpx.Response:
        """POST /periodic/{period}[/{date}] — append to periodic note (creates if missing)."""
        url = f"/periodic/{period}/{date}" if date else f"/periodic/{period}"
        return await self._request(
            "POST", url, headers={"Content-Type": "text/markdown"}, content=content
        )

    async def delete_periodic(
        self, period: str, *, date: str = ""
    ) -> httpx.Response:
        """DELETE /periodic/{period}[/{date}]."""
        url = f"/periodic/{period}/{date}" if date else f"/periodic/{period}"
        return await self._request("DELETE", url)

    async def patch_periodic(
        self,
        period: str,
        content: str,
        *,
        date: str = "",
        target_type: str = "heading",
        target: str = "",
        operation: str = "append",
        create_if_missing: bool = False,
    ) -> httpx.Response:
        """PATCH /periodic/{period}[/{date}] — surgical edit on periodic note."""
        url = f"/periodic/{period}/{date}" if date else f"/periodic/{period}"
        headers: dict[str, str] = {
            "Content-Type": "text/markdown",
            "Target-Type": target_type,
            "Target": target,
            "Operation": operation,
        }
        if create_if_missing:
            headers["Create-Target-If-Missing"] = "true"
        return await self._request("PATCH", url, headers=headers, content=content)

    async def put_active(self, content: str) -> httpx.Response:
        """PUT /active/ — replace the content of the currently-open note."""
        return await self._request(
            "PUT",
            "/active/",
            headers={"Content-Type": "text/markdown"},
            content=content,
        )

    async def post_active(self, content: str) -> httpx.Response:
        """POST /active/ — append to the currently-open note."""
        return await self._request(
            "POST",
            "/active/",
            headers={"Content-Type": "text/markdown"},
            content=content,
        )

    async def list_commands(self) -> list[dict[str, Any]]:
        """GET /commands/ — list all available Obsidian commands."""
        resp = await self._request("GET", "/commands/")
        return resp.json()  # type: ignore[no-any-return]

    async def run_command(self, command_id: str) -> httpx.Response:
        """POST /commands/{id}/ — execute an Obsidian command."""
        from urllib.parse import quote

        return await self._request("POST", f"/commands/{quote(command_id)}/")

    async def open_in_ui(
        self, path: str, *, new_leaf: bool = True
    ) -> httpx.Response:
        """POST /open/{path} — bring a note into focus in Obsidian."""
        leaf = "true" if new_leaf else "false"
        return await self._request(
            "POST", f"/open/{_encode_path(path)}?newLeaf={leaf}"
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        content: str | None = None,
    ) -> httpx.Response:
        try:
            resp = await self._http.request(method, url, headers=headers, content=content)
        except httpx.ConnectError as exc:
            raise PluginUnavailableError("Connection refused") from exc
        except httpx.TimeoutException as exc:
            raise PluginUnavailableError("Connection timeout") from exc

        if resp.status_code == 401:
            raise AuthenticationError("Invalid or expired API key (401)")
        resp.raise_for_status()
        return resp


def _safe_header(value: str) -> str:
    """Strip CRLF sequences to prevent HTTP header injection.

    Used for headers the Obsidian REST API reads verbatim (no URL-decoding):
    Target-Type, Operation, Target-Delimiter. These are ASCII enums/symbols,
    so stripping CRLF is sufficient.
    """
    return value.replace("\r", "").replace("\n", "")


def _encode_header(value: str) -> str:
    """Percent-encode a header value so it is ASCII-safe for HTTP transport.

    HTTP header values must be Latin-1 encodable; httpx raises
    ``UnicodeEncodeError`` on code points above U+00FF (e.g. the em-dash
    U+2014 that appears in many vault headings). The Obsidian Local REST API
    URL-decodes the ``Target`` header (``decodeURIComponent``), and its OpenAPI
    spec states the value *must* be URL-encoded when it contains non-ASCII
    characters. We percent-encode with an empty safe set so the original value
    round-trips through the server's decode step. CR/LF are encoded too, so
    this also prevents header injection (superseding ``_safe_header`` for these
    fields). Plain ASCII headings are unaffected beyond reversible escaping of
    reserved characters.
    """
    from urllib.parse import quote

    return quote(value, safe="")


def _encode_path(path: str) -> str:
    """URL-encode a vault-relative path for the REST API, preserving /."""
    from urllib.parse import quote

    return quote(path, safe="/")


def _version_lt(a: str, b: str) -> bool:
    try:
        a_parts = [int(x) for x in a.split(".")]
        b_parts = [int(x) for x in b.split(".")]
        return a_parts < b_parts
    except (ValueError, AttributeError):
        return False
