from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

import httpx

from hivemind.config import FallbackMode
from hivemind.rest.errors import AuthenticationError, ObsidianRestError, PluginVersionError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from hivemind.rest.connection import ConnectionMonitor

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Backend(StrEnum):
    REST = "rest"
    FS = "fs"


class Dispatcher:
    def __init__(self, mode: FallbackMode, monitor: ConnectionMonitor) -> None:
        self._mode = mode
        self._monitor = monitor

    @property
    def mode(self) -> FallbackMode:
        return self._mode

    @property
    def monitor(self) -> ConnectionMonitor:
        return self._monitor

    def pick(self, *, prefer: Backend = Backend.REST) -> Backend:
        if self._mode == FallbackMode.FS_ONLY:
            return Backend.FS
        if self._mode == FallbackMode.REST_ONLY:
            return Backend.REST
        from hivemind.rest.connection import ConnectionState

        if prefer == Backend.REST and self._monitor.current_state == ConnectionState.CONNECTED:
            return Backend.REST
        return Backend.FS

    async def perform(
        self,
        rest_fn: Callable[[], Awaitable[T]],
        fs_fn: Callable[[], Awaitable[T]],
        *,
        tool: str,
        prefer: Backend = Backend.REST,
    ) -> T:
        backend = self.pick(prefer=prefer)
        try:
            if backend == Backend.REST:
                return await rest_fn()
            return await fs_fn()
        except (
            TimeoutError,
            ObsidianRestError,
            httpx.HTTPError,
            ConnectionError,
        ) as exc:
            if isinstance(exc, (AuthenticationError, PluginVersionError)):
                raise
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                raise
            if self._mode == FallbackMode.AUTO and backend == Backend.REST:
                logger.warning("REST failed for %s, falling back to FS: %s", tool, exc)
                self._monitor.mark_degraded(exc)
                return await fs_fn()
            raise

    def require_rest(self, tool: str) -> None:
        """Raise if REST is not available. For REST-only tools."""
        backend = self.pick(prefer=Backend.REST)
        if backend != Backend.REST:
            msg = (
                f'{{"error": "REST_UNAVAILABLE", "tool": "{tool}",'
                f' "suggestion": "Obsidian must be running for this tool"}}'
            )
            raise RestUnavailableError(msg)


class RestUnavailableError(Exception):
    pass
