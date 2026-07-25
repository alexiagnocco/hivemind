"""Tests for embedding backends, cosine, and the backend factory."""

from __future__ import annotations

from types import SimpleNamespace

from hivemind.scoring.embeddings import (
    HashingEmbeddingBackend,
    cosine,
    embed_text_for_note,
    get_embedding_backend,
    tokenize,
)


class TestCosine:
    def test_identical(self) -> None:
        assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0

    def test_orthogonal(self) -> None:
        assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_opposite(self) -> None:
        assert cosine([1.0, 0.0], [-1.0, 0.0]) == -1.0

    def test_degenerate(self) -> None:
        assert cosine([], [1.0]) == 0.0
        assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestHashingBackend:
    def test_deterministic_across_instances(self) -> None:
        a = HashingEmbeddingBackend(dim=64).embed(["git rebase workflow"])[0]
        b = HashingEmbeddingBackend(dim=64).embed(["git rebase workflow"])[0]
        assert a == b

    def test_l2_normalized(self) -> None:
        vec = HashingEmbeddingBackend(dim=64).embed(["hello world"])[0]
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-9

    def test_empty_text_is_zero_vector(self) -> None:
        vec = HashingEmbeddingBackend(dim=32).embed([""])[0]
        assert vec == [0.0] * 32

    def test_overlap_scores_higher_than_disjoint(self) -> None:
        be = HashingEmbeddingBackend(dim=256)
        q = be.embed(["git rebase merge conflict"])[0]
        related = be.embed(["resolving a git merge conflict"])[0]
        unrelated = be.embed(["sql window function syntax"])[0]
        assert cosine(q, related) > cosine(q, unrelated)

    def test_dim_floor(self) -> None:
        assert HashingEmbeddingBackend(dim=1).dim == 8


def test_tokenize() -> None:
    assert tokenize("Git Rebase, v2!") == ["git", "rebase", "v2"]


def test_embed_text_for_note_includes_fields(make_note) -> None:
    note = make_note(
        "n.md", title="My Title", summary="the summary", preview="the preview",
        tags=["git", "sql"],
    )
    text = embed_text_for_note(note)
    assert "My Title" in text
    assert "the summary" in text
    assert "the preview" in text
    assert "git" in text


class TestFactory:
    @staticmethod
    def _settings(backend: str, *, model_dir: str = "", dim: int = 128) -> SimpleNamespace:
        return SimpleNamespace(
            hivemind_embeddings_backend=backend,
            hivemind_embeddings_model_dir=model_dir,
            hivemind_embeddings_dim=dim,
        )

    def test_none_disables(self) -> None:
        assert get_embedding_backend(self._settings("none")) is None

    def test_hashing(self) -> None:
        be = get_embedding_backend(self._settings("hashing", dim=99))
        assert isinstance(be, HashingEmbeddingBackend)
        assert be.dim == 99

    def test_auto_without_model_falls_back_to_hashing(self) -> None:
        be = get_embedding_backend(self._settings("auto"))
        assert isinstance(be, HashingEmbeddingBackend)

    def test_onnx_without_model_falls_back_to_hashing(self) -> None:
        be = get_embedding_backend(self._settings("onnx"))
        assert isinstance(be, HashingEmbeddingBackend)

    def test_unknown_falls_back_to_hashing(self) -> None:
        be = get_embedding_backend(self._settings("wobble"))
        assert isinstance(be, HashingEmbeddingBackend)
