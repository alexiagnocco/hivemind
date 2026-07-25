"""Shared fixtures for the hivemind test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from hivemind.model.note import Note
from hivemind.scoring.embeddings import HashingEmbeddingBackend

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def make_note() -> Callable[..., Note]:
    """Factory for Note objects with sensible defaults."""

    def _make(
        path: str,
        *,
        title: str = "",
        summary: str = "",
        preview: str = "",
        tags: list[str] | None = None,
        updated: str = "2026-05-01",
        domain: str = "",
        inbound: int = 0,
        status: str = "active",
        basename: str | None = None,
    ) -> Note:
        return Note(
            path=path,
            title=title,
            basename=basename if basename is not None else path.split("/")[-1].removesuffix(".md"),
            summary=summary,
            preview=preview,
            tags=tags or [],
            updated=updated,
            domain=domain,
            inboundCount=inbound,
            status=status,
        )

    return _make


@pytest.fixture
def hashing_backend() -> HashingEmbeddingBackend:
    return HashingEmbeddingBackend(dim=64)
