"""Heading-based note chunking with Contextual Chunk Headers (CCH).

Splits a note body at ``##``/``###`` heading boundaries (code-fence aware),
merges small sections into their successor, and hard-splits oversized chunks
at paragraph boundaries. Chunks never overlap and are exact substrings of the
body, so the round-trip invariant holds by construction:

    frontmatter + "".join(chunk.text for chunk in chunks) == source

For embedding, each chunk is prefixed with a CCH header
``[Note: title | path | section breadcrumb | Tags: ...]`` that carries the
note-level context into the vector. The header is embedded but never returned
to clients. ``embed_hash = sha256(header ‖ chunk)`` identifies the embedded
text, so renaming or retagging a note changes the hash and invalidates the
cached vector even when the chunk body is unchanged.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Sections smaller than this (word count) are merged into the next section.
MIN_WORDS = 80
# Chunks larger than this (word count) are hard-split at paragraph boundaries.
MAX_WORDS = 500

_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
# Frontmatter delimiters are whole lines of exactly `---` (CRLF-tolerant); a
# `---` embedded in a YAML value must not close the block.
_FM_OPEN_RE = re.compile(r"---[ \t]*\r?\n")
_FM_CLOSE_RE = re.compile(r"^---[ \t]*\r?$", re.MULTILINE)
# Paragraph boundary: blank line in either LF or CRLF form.
_PARA_SEP_RE = re.compile(r"(\r?\n\r?\n)")


@dataclass
class Chunk:
    """One retrievable slice of a note body.

    ``text`` is an exact substring of the body. ``anchor`` is the governing
    heading's text (usable as an Obsidian ``[[note#anchor]]`` target; empty for
    the pre-heading preamble). ``section`` is the heading breadcrumb, e.g.
    ``"Design > Trade-offs"``.
    """

    text: str
    anchor: str = ""
    section: str = ""

    @property
    def words(self) -> int:
        return len(self.text.split())


def split_frontmatter(source: str) -> tuple[str, str]:
    """Split ``source`` into (frontmatter block incl. delimiters, body).

    The two parts always concatenate back to ``source`` exactly.
    """
    opening = _FM_OPEN_RE.match(source)
    if opening is None:
        return "", source
    closing = _FM_CLOSE_RE.search(source, opening.end())
    if closing is None:
        return "", source
    return source[: closing.end()], source[closing.end() :]


def _split_at_headings(body: str) -> list[Chunk]:
    """Partition the body into heading-delimited sections (fence-aware)."""
    sections: list[Chunk] = []
    current_lines: list[str] = []
    current_anchor = ""
    current_section = ""
    h2_context = ""
    in_fence = False
    fence_marker = ""

    def flush() -> None:
        if current_lines:
            sections.append(
                Chunk(text="".join(current_lines), anchor=current_anchor,
                      section=current_section)
            )

    for line in body.splitlines(keepends=True):
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
        heading = None if in_fence else _HEADING_RE.match(line)
        if heading:
            flush()
            current_lines = []
            level, text = heading.group(1), heading.group(2)
            if level == "##":
                h2_context = text
                current_section = text
            else:
                current_section = f"{h2_context} > {text}" if h2_context else text
            current_anchor = text
        current_lines.append(line)

    flush()
    return sections


def _merge_small(sections: list[Chunk], min_words: int) -> list[Chunk]:
    """Merge sub-minimum sections into their successor (predecessor for the tail).

    A merged chunk keeps the anchor/breadcrumb of its first constituent, since
    that is where the merged text starts.
    """
    merged: list[Chunk] = []
    for sec in sections:
        if merged and merged[-1].words < min_words:
            prev = merged[-1]
            merged[-1] = Chunk(
                text=prev.text + sec.text, anchor=prev.anchor, section=prev.section
            )
        else:
            merged.append(sec)
    if len(merged) > 1 and merged[-1].words < min_words:
        tail = merged.pop()
        prev = merged[-1]
        merged[-1] = Chunk(
            text=prev.text + tail.text, anchor=prev.anchor, section=prev.section
        )
    return merged


def _hard_split(chunk: Chunk, max_words: int) -> list[Chunk]:
    """Split an oversized chunk at paragraph (blank-line) boundaries.

    Greedy grouping keeps every piece at or under ``max_words`` unless a single
    paragraph alone exceeds it (indivisible). All pieces keep the source
    chunk's anchor/breadcrumb, and piece texts concatenate back exactly.
    """
    if chunk.words <= max_words:
        return [chunk]

    # Split keeping the separators, then reattach each separator to the
    # paragraph it follows — units concatenate back to the text exactly,
    # in LF and CRLF notes alike.
    parts = _PARA_SEP_RE.split(chunk.text)
    units = ["".join(parts[i : i + 2]) for i in range(0, len(parts), 2)]

    pieces: list[Chunk] = []
    buf = ""
    buf_words = 0
    for unit in units:
        words = len(unit.split())
        if buf and buf_words + words > max_words:
            pieces.append(Chunk(text=buf, anchor=chunk.anchor, section=chunk.section))
            buf = ""
            buf_words = 0
        buf += unit
        buf_words += words
    if buf:
        pieces.append(Chunk(text=buf, anchor=chunk.anchor, section=chunk.section))
    return pieces


def chunk_note(
    source: str,
    *,
    min_words: int = MIN_WORDS,
    max_words: int = MAX_WORDS,
) -> tuple[str, list[Chunk]]:
    """Chunk a full note. Returns ``(frontmatter, chunks)``.

    Invariant: ``frontmatter + "".join(c.text for c in chunks) == source``.
    """
    frontmatter, body = split_frontmatter(source)
    if not body:
        return frontmatter, []
    sections = _split_at_headings(body)
    merged = _merge_small(sections, min_words)
    chunks: list[Chunk] = []
    for chunk in merged:
        chunks.extend(_hard_split(chunk, max_words))
    return frontmatter, chunks


def cch_header(*, title: str, path: str, section: str, tags: list[str]) -> str:
    """Contextual Chunk Header — prepended for embedding only, never returned."""
    return f"[Note: {title} | {path} | {section} | Tags: {', '.join(tags)}]"


def embed_text_for_chunk(header: str, chunk_text: str) -> str:
    """The exact text that gets embedded: CCH header ‖ chunk."""
    return f"{header}\n{chunk_text}"


def embed_hash(header: str, chunk_text: str) -> str:
    """sha256(header ‖ chunk) — identity of the embedded text.

    Changes when the chunk body changes OR when any CCH component (title,
    path, breadcrumb, tags) changes, which is what makes retag/rename
    staleness detectable without file-level bookkeeping.
    """
    return hashlib.sha256(
        embed_text_for_chunk(header, chunk_text).encode("utf-8")
    ).hexdigest()
