from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from hivemind.rest.errors import AuthenticationError

if TYPE_CHECKING:
    from hivemind.rest.client import ObsidianRestClient

logger = logging.getLogger(__name__)


class ConnectionState(StrEnum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    UNCONFIGURED = "UNCONFIGURED"


class ConnectionMonitor:
    def __init__(
        self,
        client: ObsidianRestClient,
        interval: int = 30,
        *,
        unconfigured: bool = False,
    ) -> None:
        self._client = client
        self._interval = interval
        self._state = ConnectionState.UNCONFIGURED if unconfigured else ConnectionState.DISCONNECTED
        self._plugin_version: str = ""
        self._obsidian_version: str = ""
        self._last_check: str = ""
        self._error_message: str = ""
        self._consecutive_failures: int = 0
        self._task: asyncio.Task[None] | None = None

    @property
    def current_state(self) -> ConnectionState:
        return self._state

    @property
    def plugin_version(self) -> str:
        return self._plugin_version

    @property
    def obsidian_version(self) -> str:
        return self._obsidian_version

    @property
    def last_check_iso(self) -> str:
        return self._last_check

    @property
    def error_message(self) -> str:
        return self._error_message

    def mark_degraded(self, exc: Exception) -> None:
        if self._state == ConnectionState.CONNECTED:
            self._state = ConnectionState.DEGRADED
            self._error_message = str(exc)
            logger.warning("Connection degraded: %s", exc)

    async def start(self) -> None:
        if self._state == ConnectionState.UNCONFIGURED:
            logger.info("No API key configured; skipping connection monitor")
            return
        await self._refresh()
        self._task = asyncio.create_task(self._loop(), name="connection-monitor")

    async def stop(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval)
                await self._refresh()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Connection monitor loop exited unexpectedly", exc_info=True)

    async def _refresh(self) -> None:
        self._last_check = datetime.now(UTC).isoformat()
        try:
            status = await self._client.ping()
            self._state = ConnectionState.CONNECTED
            self._plugin_version = status.plugin_version
            self._obsidian_version = status.obsidian_version
            self._error_message = ""
            self._consecutive_failures = 0
        except AuthenticationError as exc:
            self._state = ConnectionState.DISCONNECTED
            self._error_message = str(exc)
            self._consecutive_failures += 1
            logger.warning("Auth failed: %s", exc)
        except Exception as exc:
            self._consecutive_failures += 1
            self._error_message = str(exc)
            if self._consecutive_failures >= 3:
                self._state = ConnectionState.DISCONNECTED
            else:
                self._state = ConnectionState.DEGRADED
            logger.debug(
                "Ping failed (%d consecutive): %s", self._consecutive_failures, exc
            )
