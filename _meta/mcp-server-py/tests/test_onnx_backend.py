"""Validates the real OnnxEmbeddingBackend inference path against a tiny,
committed ONNX fixture (a Gather-over-embedding-table model).

Runs only when the optional ``embeddings`` extra (onnxruntime + tokenizers) is
installed; skips otherwise. This exercises the genuine onnxruntime session,
attention-mask mean pooling, and L2 normalization without any model download.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("onnxruntime")
pytest.importorskip("tokenizers")

from hivemind.scoring.embeddings import (
    OnnxEmbeddingBackend,
    cosine,
    get_embedding_backend,
)

FIXTURE = Path(__file__).parent / "fixtures" / "tiny-onnx"


@pytest.fixture
def backend() -> OnnxEmbeddingBackend:
    return OnnxEmbeddingBackend(str(FIXTURE))


def test_dim_inferred_from_model(backend: OnnxEmbeddingBackend) -> None:
    assert backend.dim == 8
    assert backend.name.startswith("onnx:")


def test_embeds_are_l2_normalized(backend: OnnxEmbeddingBackend) -> None:
    vecs = backend.embed(["git rebase", "sql window function"])
    assert len(vecs) == 2
    for v in vecs:
        assert len(v) == 8
        assert sum(x * x for x in v) == pytest.approx(1.0, abs=1e-5)


def test_deterministic(backend: OnnxEmbeddingBackend) -> None:
    assert backend.embed(["git merge conflict"]) == backend.embed(["git merge conflict"])


def test_shared_tokens_raise_similarity(backend: OnnxEmbeddingBackend) -> None:
    q, related, unrelated = backend.embed(
        ["git merge conflict", "git merge branch", "sql window function"]
    )
    assert cosine(q, related) > cosine(q, unrelated)


def test_padding_is_masked_out(backend: OnnxEmbeddingBackend) -> None:
    """Regression: the fixture tokenizer pads to a fixed length, so [PAD] tokens
    must be excluded from mean pooling. If they leak in (the original bug, where
    the attention mask was derived from len(ids)), pad rows dominate and all
    short texts collapse toward identical vectors. Distinct single tokens must
    therefore stay well apart."""
    git, sql = backend.embed(["git", "sql"])
    assert cosine(git, sql) < 0.5  # would be ~1.0 if padding polluted the pool



def test_empty_input(backend: OnnxEmbeddingBackend) -> None:
    assert backend.embed([]) == []


def test_missing_assets_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OnnxEmbeddingBackend(str(tmp_path))


def test_factory_uses_onnx_when_model_dir_valid() -> None:
    from types import SimpleNamespace

    settings = SimpleNamespace(
        hivemind_embeddings_backend="onnx",
        hivemind_embeddings_model_dir=str(FIXTURE),
        hivemind_embeddings_dim=256,
    )
    backend = get_embedding_backend(settings)
    assert isinstance(backend, OnnxEmbeddingBackend)
