"""Unit tests for build_status_response — the embedding_backend field.

Covers the three states an operator must be able to distinguish from
``hive_status`` output: a real semantic backend (onnx), the lexical hashing
fallback, and dense retrieval disabled entirely (null). These are pure unit
tests against build_status_response — no FastMCP machinery required.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from hivemind.config import Settings
from hivemind.rest.connection import ConnectionState
from hivemind.scoring.embeddings import HashingEmbeddingBackend
from hivemind.tools.status import build_status_response


def _monitor() -> SimpleNamespace:
    return SimpleNamespace(
        current_state=ConnectionState.DISCONNECTED,
        plugin_version=None,
        obsidian_version=None,
        last_check_iso=None,
        error_message=None,
    )


def _settings(tmp_path, *, backend_mode: str = "hashing") -> Settings:
    return Settings(
        obsidian_api_key="k",
        hive_path=tmp_path,
        hivemind_embeddings_backend=backend_mode,
        hivemind_embeddings_dim=64,
    )


def test_hashing_backend_surfaced(tmp_path) -> None:
    backend = HashingEmbeddingBackend(dim=64)
    result = json.loads(build_status_response(_settings(tmp_path), _monitor(), backend=backend))
    assert result["embedding_backend"] == {"name": "hashing-64", "dim": 64}


def test_none_backend_produces_null(tmp_path) -> None:
    # When dense retrieval is disabled the key is present with a null value
    # (not omitted), so consumers get a stable payload shape.
    result = json.loads(
        build_status_response(_settings(tmp_path, backend_mode="none"), _monitor(), backend=None)
    )
    assert "embedding_backend" in result
    assert result["embedding_backend"] is None


def test_onnx_backend_surfaced(tmp_path) -> None:
    """Skipped automatically when onnxruntime/tokenizers are not installed."""
    pytest.importorskip("onnxruntime")
    pytest.importorskip("tokenizers")

    import pathlib

    # Deferred import: onnxruntime/tokenizers may be absent on a base dev
    # install; the importorskip calls above guard this at runtime.
    from hivemind.scoring.embeddings import OnnxEmbeddingBackend

    fixture_dir = pathlib.Path(__file__).parent / "fixtures" / "tiny-onnx"
    if not (fixture_dir / "model.onnx").is_file():
        pytest.skip("tiny-onnx fixture not present")

    backend = OnnxEmbeddingBackend(str(fixture_dir))
    # The fixture yields name='onnx:tiny-onnx', dim=8 — not production values.
    result = json.loads(build_status_response(_settings(tmp_path), _monitor(), backend=backend))
    eb = result["embedding_backend"]
    assert eb is not None
    assert eb["name"].startswith("onnx:")
    assert isinstance(eb["dim"], int) and eb["dim"] > 0
