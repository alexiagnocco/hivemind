"""Tests for heading-based chunking + CCH (Phase 3.2).

Covers the property-based round-trip invariant
(frontmatter + concat(chunks) == source), size bounds, CCH embed_hash
staleness on retag/rename, and the ChunkStore's incremental behavior.
"""

from __future__ import annotations

import json

from hypothesis import given
from hypothesis import strategies as st

from hivemind.chunking import (
    MAX_WORDS,
    MIN_WORDS,
    cch_header,
    chunk_note,
    embed_hash,
    embed_text_for_chunk,
    split_frontmatter,
)
from hivemind.model.note import Note
from hivemind.scoring.embeddings import HashingEmbeddingBackend
from hivemind.state.chunk_store import ChunkStore

# ---------------------------------------------------------------------------
# Round-trip invariant (property-based)
# ---------------------------------------------------------------------------

_frontmatter = st.sampled_from([
    "",
    "---\ncreated: 2026-07-01\ntags: [ai, meta]\n---\n",
    "---\nstatus: active\n---",
])

_body_fragments = st.lists(
    st.sampled_from([
        "plain paragraph text here\n",
        "## Heading A\n",
        "### Sub heading\n",
        "#### Not a boundary\n",
        "\n",
        "- list item\n",
        "```\n## not a heading, fenced\n```\n",
        "word " * 120 + "\n",
        "text without trailing newline",
        "~~~\n### fenced tilde\n~~~\n",
        "[[wikilink]] and *markup*\n",
        "crlf paragraph\r\n\r\n",
        "## CRLF heading\r\n",
        "word " * 120 + "\r\n\r\n",
    ]),
    max_size=12,
)


@given(fm=_frontmatter, fragments=_body_fragments)
def test_round_trip_invariant(fm: str, fragments: list[str]) -> None:
    source = fm + "".join(fragments)
    frontmatter, chunks = chunk_note(source)
    assert frontmatter + "".join(c.text for c in chunks) == source


@given(text=st.text(max_size=2000))
def test_round_trip_invariant_arbitrary_text(text: str) -> None:
    frontmatter, chunks = chunk_note(text)
    assert frontmatter + "".join(c.text for c in chunks) == text


@given(text=st.text(max_size=1000))
def test_split_frontmatter_always_concats(text: str) -> None:
    fm, body = split_frontmatter(text)
    assert fm + body == text


# ---------------------------------------------------------------------------
# Size bounds
# ---------------------------------------------------------------------------


@given(fragments=_body_fragments)
def test_chunks_never_exceed_max_unless_indivisible(fragments: list[str]) -> None:
    import re

    _fm, chunks = chunk_note("".join(fragments))
    for c in chunks:
        # A chunk may exceed MAX_WORDS only if it has no paragraph split point
        # (blank line, LF or CRLF).
        assert c.words <= MAX_WORDS or not re.search(r"\r?\n\r?\n", c.text.strip())


def test_small_sections_merged_forward() -> None:
    source = "## A\ntiny\n## B\n" + ("word " * (MIN_WORDS + 20)) + "\n"
    _fm, chunks = chunk_note(source)
    # "A" alone is far below MIN_WORDS, so it merges with section B.
    assert len(chunks) == 1
    assert chunks[0].anchor == "A"


def test_trailing_small_section_merges_backward() -> None:
    source = ("## A\n" + "word " * (MIN_WORDS + 20) + "\n") + "## B\ntiny\n"
    _fm, chunks = chunk_note(source)
    assert len(chunks) == 1
    assert chunks[0].anchor == "A"


def test_oversized_section_hard_splits_at_paragraphs() -> None:
    para = "word " * 200
    source = f"## Big\n{para}\n\n{para}\n\n{para}\n\n{para}\n"
    _fm, chunks = chunk_note(source)
    assert len(chunks) >= 2
    assert all(c.words <= MAX_WORDS for c in chunks)
    assert all(c.anchor == "Big" for c in chunks)
    assert "".join(c.text for c in chunks) == source


def test_crlf_oversized_section_hard_splits() -> None:
    # Regression: "\r\n\r\n" contains no "\n\n", so CRLF notes were never
    # hard-split and silently violated MAX_WORDS.
    para = "word " * 200
    source = f"## Big\r\n{para}\r\n\r\n{para}\r\n\r\n{para}\r\n\r\n{para}\r\n"
    _fm, chunks = chunk_note(source)
    assert len(chunks) >= 2
    assert all(c.words <= MAX_WORDS for c in chunks)
    assert "".join(c.text for c in chunks) == source


def test_single_giant_paragraph_stays_whole() -> None:
    source = "## Big\n" + "word " * (MAX_WORDS * 2) + "\n"
    _fm, chunks = chunk_note(source)
    assert len(chunks) == 1
    assert chunks[0].words > MAX_WORDS  # indivisible — no paragraph boundary


# ---------------------------------------------------------------------------
# Anchors / breadcrumbs / fences
# ---------------------------------------------------------------------------


def _big(text: str) -> str:
    return text + "\n" + "word " * (MIN_WORDS + 10) + "\n"


def test_breadcrumbs_track_h2_context() -> None:
    source = _big("## Design") + _big("### Trade-offs") + _big("## Rollout")
    _fm, chunks = chunk_note(source)
    sections = [c.section for c in chunks]
    assert sections == ["Design", "Design > Trade-offs", "Rollout"]
    assert [c.anchor for c in chunks] == ["Design", "Trade-offs", "Rollout"]


def test_preamble_has_empty_anchor() -> None:
    source = "intro text\n" + "word " * (MIN_WORDS + 10) + "\n" + _big("## First")
    _fm, chunks = chunk_note(source)
    assert chunks[0].anchor == ""
    assert chunks[0].section == ""


def test_headings_inside_code_fences_are_not_boundaries() -> None:
    fenced = "```\n## fenced heading\n```\n" + "word " * (MIN_WORDS + 10) + "\n"
    source = _big("## Real") + fenced
    _fm, chunks = chunk_note(source)
    assert all(c.anchor != "fenced heading" for c in chunks)


def test_frontmatter_only_note_yields_no_chunks() -> None:
    source = "---\ncreated: 2026-07-01\n---"
    fm, chunks = chunk_note(source)
    assert fm == source
    assert chunks == []


def test_frontmatter_close_must_be_at_line_start() -> None:
    # Regression: a `---` inside a YAML value used to close the block, leaking
    # the rest of the frontmatter into the (embedded) chunk text.
    source = "---\ntitle: a---b\ntags: [x]\n---\nbody text\n"
    fm, body = split_frontmatter(source)
    assert fm == "---\ntitle: a---b\ntags: [x]\n---"
    assert body == "\nbody text\n"


def test_frontmatter_crlf_delimiters() -> None:
    source = "---\r\ncreated: 2026-07-01\r\n---\r\nbody\r\n"
    fm, body = split_frontmatter(source)
    assert fm.endswith("---\r")
    assert body == "\nbody\r\n"
    assert fm + body == source


def test_horizontal_rule_start_is_not_frontmatter() -> None:
    # A leading `----` (hr) plus a later `---` line must not be eaten as
    # frontmatter — the opening delimiter is a line of exactly `---`.
    source = "----\nsome text\n---\nmore text\n"
    fm, body = split_frontmatter(source)
    assert fm == ""
    assert body == source


def test_note_with_no_headings_is_one_chunk() -> None:
    source = "just a paragraph\n\nand another\n"
    _fm, chunks = chunk_note(source)
    assert len(chunks) == 1
    assert chunks[0].anchor == ""


def test_no_heading_giant_paragraph_round_trips() -> None:
    # No headings AND no paragraph boundaries AND > MAX_WORDS: indivisible.
    source = "word " * (MAX_WORDS * 2)
    fm, chunks = chunk_note(source)
    assert fm == ""
    assert len(chunks) == 1
    assert chunks[0].words > MAX_WORDS
    assert "".join(c.text for c in chunks) == source


# ---------------------------------------------------------------------------
# CCH embed_hash staleness
# ---------------------------------------------------------------------------


def test_embed_hash_changes_on_retag() -> None:
    chunk = "## A\nsome section text\n"
    h_before = cch_header(title="T", path="p.md", section="A", tags=["ai"])
    h_after = cch_header(title="T", path="p.md", section="A", tags=["ai", "meta"])
    assert embed_hash(h_before, chunk) != embed_hash(h_after, chunk)


def test_embed_hash_changes_on_rename() -> None:
    chunk = "body\n"
    h1 = cch_header(title="Old title", path="a.md", section="", tags=[])
    h2 = cch_header(title="New title", path="a.md", section="", tags=[])
    h3 = cch_header(title="Old title", path="b.md", section="", tags=[])
    assert len({embed_hash(h, chunk) for h in (h1, h2, h3)}) == 3


def test_embed_hash_stable_for_identical_inputs() -> None:
    h = cch_header(title="T", path="p.md", section="S", tags=["x"])
    assert embed_hash(h, "text") == embed_hash(h, "text")


def test_header_is_embedded_but_not_part_of_chunk_text() -> None:
    h = cch_header(title="T", path="p.md", section="S", tags=[])
    assert embed_text_for_chunk(h, "chunk body").startswith("[Note: T | p.md | S |")
    # chunk_note never returns header-bearing text (chunks are substrings).
    _fm, chunks = chunk_note("## S\nchunk body\n")
    assert all("[Note:" not in c.text for c in chunks)


# ---------------------------------------------------------------------------
# ChunkStore incremental behavior
# ---------------------------------------------------------------------------


def _note(path: str, title: str, tags: list[str] | None = None) -> Note:
    return Note(path=path, title=title, basename=path.split("/")[-1].removesuffix(".md"),
                tags=tags or [])


def _write(tmp_path, rel: str, text: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_store_builds_persists_and_gitignored_location(tmp_path) -> None:
    _write(tmp_path, "a.md", "## One\n" + "word " * 100 + "\n## Two\n" + "word " * 100)
    store = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=32))
    index = store.index([_note("a.md", "A")])
    assert len(index["a.md"]) == 2
    assert all(r.vector is not None for r in index["a.md"])
    assert (tmp_path / "_meta" / "hive-chunks.json").is_file()


def test_store_reuses_cache_for_unchanged_files(tmp_path) -> None:
    _write(tmp_path, "a.md", "## One\nbody text here\n")
    store = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=32))
    store.index([_note("a.md", "A")])
    raw1 = (tmp_path / "_meta" / "hive-chunks.json").read_text(encoding="utf-8")
    # Fresh store instance (new process) — same file content, no re-embed.
    store2 = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=32))
    index = store2.index([_note("a.md", "A")])
    raw2 = (tmp_path / "_meta" / "hive-chunks.json").read_text(encoding="utf-8")
    assert raw1 == raw2
    assert len(index["a.md"]) == 1


def test_store_retag_invalidates_vectors(tmp_path) -> None:
    _write(tmp_path, "a.md", "## One\nbody text here\n")
    store = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=32))
    before = store.index([_note("a.md", "A", tags=["ai"])])
    hash_before = before["a.md"][0].embed_hash
    # Same file bytes, different manifest tags → new embed_hash, re-embedded.
    after = store.index([_note("a.md", "A", tags=["ai", "meta"])])
    hash_after = after["a.md"][0].embed_hash
    assert hash_before != hash_after
    assert after["a.md"][0].vector is not None
    data = json.loads((tmp_path / "_meta" / "hive-chunks.json").read_text("utf-8"))
    assert hash_after in data["vectors"]
    assert hash_before not in data["vectors"]  # stale vector pruned


def test_store_without_backend_yields_chunks_without_vectors(tmp_path) -> None:
    _write(tmp_path, "a.md", "## One\nbody text here\n")
    store = ChunkStore(tmp_path, None)
    index = store.index([_note("a.md", "A")])
    assert len(index["a.md"]) == 1
    assert index["a.md"][0].vector is None


def test_store_frontmatter_only_note_yields_empty_chunk_list(tmp_path) -> None:
    _write(tmp_path, "a.md", "---\ncreated: 2026-07-01\n---")
    store = ChunkStore(tmp_path, None)
    index = store.index([_note("a.md", "A")])
    assert index["a.md"] == []


def test_store_prunes_deleted_notes(tmp_path) -> None:
    _write(tmp_path, "a.md", "## One\nbody\n")
    _write(tmp_path, "b.md", "## Two\nbody\n")
    store = ChunkStore(tmp_path, HashingEmbeddingBackend(dim=32))
    store.index([_note("a.md", "A"), _note("b.md", "B")])
    store.index([_note("a.md", "A")])
    data = json.loads((tmp_path / "_meta" / "hive-chunks.json").read_text("utf-8"))
    assert set(data["notes"]) == {"a.md"}
