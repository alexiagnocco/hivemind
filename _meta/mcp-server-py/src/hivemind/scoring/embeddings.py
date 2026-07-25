"""Dense-embedding backends for hybrid retrieval.

hive_retrieve fuses the existing keyword/metadata composite score with a
dense-vector cosine similarity so that conceptually relevant notes surface even
when they share no keywords with the query.

Two backends are provided:

* :class:`HashingEmbeddingBackend` — a dependency-free, deterministic
  feature-hashing bag-of-words embedding. Always available; used as the
  graceful fallback and in tests. Lexical, not semantic.
* :class:`OnnxEmbeddingBackend` — a real sentence-transformer (e.g.
  ``all-MiniLM-L6-v2``) exported to ONNX, run via ``onnxruntime`` with a
  ``tokenizers`` tokenizer. This is the semantic backend; its dependencies live
  in the optional ``embeddings`` extra and the model weights are provisioned
  out-of-band (see ``scripts/fetch-embedding-model.py``).

The factory :func:`get_embedding_backend` selects a backend from settings,
degrading to hashing (and finally to ``None`` → keyword-only retrieval) when the
semantic backend cannot be constructed.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from hivemind.config import Settings
    from hivemind.model.note import Note

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word/number tokenization shared by lexical backends."""
    return _TOKEN_RE.findall(text.lower())


def embed_text_for_note(note: Note) -> str:
    """Build the text representation of a note used for embedding.

    Uses only manifest-resident fields (no file reads): title, tags, summary,
    and preview. Title and tags are repeated to weight them slightly higher.
    """
    parts = [
        note.title or note.basename or "",
        note.title or "",
        " ".join(note.tags),
        " ".join(note.tags),
        note.summary or "",
        note.preview or "",
    ]
    return "\n".join(p for p in parts if p).strip()


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors. 0.0 on degenerate input."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=False):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Embeds text into fixed-dimensional dense vectors."""

    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one L2-normalized vector per input text."""
        ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0.0:
        return vec
    return [v / norm for v in vec]


class HashingEmbeddingBackend:
    """Deterministic feature-hashing embedding — no external dependencies.

    Each token is hashed (SHA-1, so results are stable across processes and
    platforms, unlike Python's salted ``hash()``) into one of ``dim`` buckets
    with a signed contribution. The resulting bag-of-words vector is
    L2-normalized. This captures lexical overlap robustly and serves as the
    always-available fallback when the ONNX semantic backend is not provisioned.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = max(8, dim)
        self.name = f"hashing-{self.dim}"

    def _hash(self, token: str) -> tuple[int, float]:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % self.dim
        sign = 1.0 if digest[4] & 1 else -1.0
        return bucket, sign

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in tokenize(text):
                bucket, sign = self._hash(token)
                vec[bucket] += sign
            out.append(_l2_normalize(vec))
        return out


class OnnxEmbeddingBackend:
    """Sentence-transformer embedding via onnxruntime + tokenizers.

    Loads ``model.onnx`` and ``tokenizer.json`` from ``model_dir`` (provisioned
    by ``scripts/fetch-embedding-model.py``). Applies mean pooling over token
    embeddings with the attention mask, then L2-normalizes — the standard
    pipeline for MiniLM/BGE-style models. Dependencies (onnxruntime, tokenizers,
    numpy) are imported lazily so the base install stays light.
    """

    def __init__(self, model_dir: str, *, max_length: int = 256) -> None:
        import os

        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_path = os.path.join(model_dir, "model.onnx")
        tok_path = os.path.join(model_dir, "tokenizer.json")
        if not os.path.isfile(model_path) or not os.path.isfile(tok_path):
            raise FileNotFoundError(
                f"ONNX model assets not found in {model_dir!r} "
                "(expected model.onnx and tokenizer.json)"
            )

        self._np = np
        self._tokenizer = Tokenizer.from_file(tok_path)
        # Pad ourselves to the per-batch max; relying on the tokenizer's own
        # fixed-length padding would leave [PAD] tokens in enc.ids that must be
        # masked out (see embed()).
        self._tokenizer.no_padding()
        self._tokenizer.enable_truncation(max_length=max_length)
        self._session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"]
        )
        self._input_names = {i.name for i in self._session.get_inputs()}
        out_shape = self._session.get_outputs()[0].shape
        self.dim = int(out_shape[-1]) if isinstance(out_shape[-1], int) else 384
        self.name = f"onnx:{os.path.basename(os.path.normpath(model_dir))}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        np = self._np
        encodings = [self._tokenizer.encode(t) for t in texts]
        max_len = max((len(e.ids) for e in encodings), default=1) or 1
        input_ids = np.zeros((len(texts), max_len), dtype=np.int64)
        attention = np.zeros((len(texts), max_len), dtype=np.int64)
        for i, enc in enumerate(encodings):
            ids = enc.ids
            input_ids[i, : len(ids)] = ids
            # Use the tokenizer's own attention mask so any [PAD] tokens are
            # excluded from mean pooling — deriving it from len(ids) would
            # treat padding as real tokens and wreck the pooled embedding.
            attention[i, : len(ids)] = enc.attention_mask

        feeds: dict[str, object] = {}
        if "input_ids" in self._input_names:
            feeds["input_ids"] = input_ids
        if "attention_mask" in self._input_names:
            feeds["attention_mask"] = attention
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)

        token_embeddings = self._session.run(None, feeds)[0]  # (B, T, H)
        mask = attention[..., None].astype(np.float32)
        summed = (token_embeddings * mask).sum(axis=1)
        counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        pooled = summed / counts
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        norms = np.clip(norms, a_min=1e-12, a_max=None)
        normalized = pooled / norms
        result: list[list[float]] = normalized.astype(float).tolist()
        return result


def get_embedding_backend(settings: Settings) -> EmbeddingBackend | None:
    """Select an embedding backend from settings.

    ``hivemind_embeddings_backend``:

    * ``none`` — disable dense retrieval (keyword-only).
    * ``hashing`` — force the dependency-free hashing backend.
    * ``onnx`` — require the ONNX backend; fall back to hashing if it cannot
      be constructed.
    * ``auto`` (default) — try ONNX, then hashing.
    """
    mode = settings.hivemind_embeddings_backend.strip().lower()
    if mode == "none":
        return None

    dim = settings.hivemind_embeddings_dim
    model_dir = settings.hivemind_embeddings_model_dir

    def _hashing() -> EmbeddingBackend:
        return HashingEmbeddingBackend(dim=dim)

    if mode == "hashing":
        return _hashing()

    if mode in ("auto", "onnx"):
        if model_dir:
            try:
                backend = OnnxEmbeddingBackend(model_dir)
                logger.info("Dense retrieval using ONNX backend: %s", backend.name)
                return backend
            except Exception as exc:
                logger.warning(
                    "ONNX embedding backend unavailable (%s); "
                    "falling back to hashing backend",
                    exc,
                )
        elif mode == "onnx":
            logger.warning(
                "embeddings_backend=onnx but no model_dir configured; "
                "falling back to hashing backend"
            )
        return _hashing()

    logger.warning(
        "Unknown embeddings_backend %r; falling back to hashing backend", mode
    )
    return _hashing()
