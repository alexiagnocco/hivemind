from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from hivemind.config import FallbackMode, Settings
from hivemind.rest.client import _version_lt
from hivemind.rest.connection import ConnectionMonitor, ConnectionState

if TYPE_CHECKING:
    from hivemind.scoring.embeddings import EmbeddingBackend


def build_status_response(
    settings: Settings,
    monitor: ConnectionMonitor,
    *,
    backend: EmbeddingBackend | None = None,
) -> str:
    state = monitor.current_state
    if settings.obsidian_fallback_mode == FallbackMode.FS_ONLY:
        state_label = "DISABLED"
    else:
        state_label = state.value

    result: dict[str, Any] = {
        "state": state_label,
        "plugin_version": monitor.plugin_version or None,
        "obsidian_version": monitor.obsidian_version or None,
        "last_check": monitor.last_check_iso or None,
        "recheck_interval_sec": settings.obsidian_recheck_interval_sec,
        "fallback_mode": settings.obsidian_fallback_mode.value,
        "rest_url": settings.obsidian_rest_url,
        "hive_path": str(settings.hive_path),
        "server_version": "4.0.0",
        # Nested {name, dim} (vs the flat scalars above) groups the backend
        # identity and keeps the disabled case a single null. Name prefix
        # 'onnx:' = semantic dense retrieval, 'hashing-' = lexical fallback.
        "embedding_backend": (
            {"name": backend.name, "dim": backend.dim} if backend is not None else None
        ),
    }

    if monitor.error_message:
        result["error"] = monitor.error_message

    if state == ConnectionState.CONNECTED:
        min_ver = settings.obsidian_rest_api_version_min
        if monitor.plugin_version and _version_lt(monitor.plugin_version, min_ver):
            result["warning"] = (
                f"Plugin version {monitor.plugin_version} is below minimum {min_ver}"
            )

    return json.dumps(result, indent=2)
