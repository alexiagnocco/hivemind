"""Manifest builder — Python port of manifest-builder.ts.

Walks the vault, parses frontmatter + wikilinks, builds rich indexes,
and writes vault-manifest.json. Schema v2.0 frozen.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from engram.fs.frontmatter import parse_frontmatter
from engram.fs.paths import is_system_note

if TYPE_CHECKING:
    from pathlib import Path

EXCLUDE_DIRS = frozenset({
    ".git", ".obsidian", "_templates", "node_modules", ".claude", ".trash",
    ".venv", "_archive",
})

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
KEYWORD_RE = re.compile(r"[a-z]{4,}")
H1_RE = re.compile(r"(?:^|\n)#\s+(.+)")

STOP_WORDS = frozenset({
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "have", "been", "will",
    "each", "make", "like", "long", "look", "many", "some", "than",
    "them", "then", "this", "that", "what", "when", "with", "from",
    "into", "just", "also", "more", "most", "only", "over", "such",
    "very", "your", "about", "after", "could", "every", "first",
    "found", "great", "might", "never", "other", "should", "since",
    "still", "their", "there", "these", "thing", "think", "those",
    "through", "under", "using", "where", "which", "while", "would",
    "being", "between", "does", "done", "down", "even", "given",
    "here", "hers", "high", "keep", "know", "last", "made", "much",
    "must", "name", "next", "need", "part", "same", "show", "take",
    "time", "used", "want", "well", "were", "work", "note", "notes",
    "updated", "created", "status", "active", "type", "domain", "tags",
    "true", "false", "null", "none", "yaml", "markdown",
})

PREVIEW_LENGTH = 500


def _extract_title(text: str, stem: str) -> str:
    m = H1_RE.search(text)
    return m.group(1).strip() if m else stem


def _body_after_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3 :]


def _extract_summary(text: str, max_len: int = 150) -> str:
    body = _body_after_frontmatter(text)
    for line in body.split("\n"):
        trimmed = line.strip()
        skip_prefixes = ("#", ">", "---")
        if not trimmed or any(trimmed.startswith(p) for p in skip_prefixes):
            continue
        if trimmed.startswith("[[") or trimmed.startswith("- ["):
            continue
        if len(trimmed) > max_len:
            cut = trimmed[:max_len]
            last_space = cut.rfind(" ")
            return cut[:last_space] + "..." if last_space > 0 else cut + "..."
        return trimmed
    return ""


def _extract_preview(text: str, length: int = PREVIEW_LENGTH) -> str:
    body = _body_after_frontmatter(text).strip()
    return body[:length] + "..." if len(body) > length else body


def _extract_links(text: str) -> list[str]:
    targets: set[str] = set()
    for m in WIKILINK_RE.finditer(text):
        raw = m.group(1).strip()
        parts = raw.split("/")
        name = parts[-1].removesuffix(".md")
        targets.add(name)
    return sorted(targets)


def _extract_keywords(title: str, body_snippet: str) -> list[str]:
    source = (title + " " + body_snippet).lower()
    words = set(KEYWORD_RE.findall(source))
    return sorted(w for w in words if w not in STOP_WORDS)


def _detect_para_folder(rel_path: str) -> str:
    m1 = re.match(r"^(\d\d-\w+)", rel_path)
    if m1:
        return m1.group(1)
    m2 = re.match(r"^(memory|_meta|_templates|50-maps)", rel_path)
    if m2:
        return m2.group(1)
    return "other"


def _walk_md_files(directory: Path, root: Path) -> list[Path]:
    results: list[Path] = []
    try:
        entries = sorted(directory.iterdir(), key=lambda p: p.name)
    except OSError:
        return results
    for entry in entries:
        # Skip every dot-entry, not just the enumerated caches — .venv,
        # .pytest_cache, and future tool dirs all ship stray markdown.
        if entry.name in EXCLUDE_DIRS or entry.name.startswith("."):
            continue
        if entry.is_dir():
            results.extend(_walk_md_files(entry, root))
        elif entry.suffix == ".md":
            results.append(entry)
    return results


def build_manifest(vault_path: Path) -> dict[str, Any]:
    notes: dict[str, dict[str, Any]] = {}
    tag_index: dict[str, list[str]] = {}
    domain_index: dict[str, list[str]] = {}
    status_index: dict[str, list[str]] = {}
    type_index: dict[str, list[str]] = {}
    keyword_index: dict[str, list[str]] = {}
    inbound_links: dict[str, list[str]] = {}

    md_files = _walk_md_files(vault_path, vault_path)

    for full_path in md_files:
        try:
            text = full_path.read_text(encoding="utf-8")
        except OSError:
            continue

        rel_path = full_path.relative_to(vault_path).as_posix()
        fm = parse_frontmatter(text)
        stat = full_path.stat()
        stem = full_path.stem
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime("%Y-%m-%d")

        raw_tags = fm.get("tags")
        tags: list[str] = []
        if isinstance(raw_tags, list):
            tags = [str(t).strip().lstrip("#") for t in raw_tags if str(t).strip()]
        elif isinstance(raw_tags, str):
            tags = [t.strip().lstrip("#") for t in raw_tags.split(",") if t.strip()]

        title = _extract_title(text, stem)
        out_links = [link for link in _extract_links(text) if link != stem]

        body = _body_after_frontmatter(text)
        body_snippet = body[:200]
        keywords = _extract_keywords(title, body_snippet)
        para_folder = _detect_para_folder(rel_path)

        note: dict[str, Any] = {
            "path": rel_path,
            "title": title,
            "basename": stem,
            "paraFolder": para_folder,
            "created": str(fm.get("created", mtime)),
            "updated": str(fm.get("updated", mtime)),
            "status": str(fm.get("status", "")),
            "type": str(fm.get("type", "")),
            "domain": str(fm.get("domain", "")),
            "tags": tags,
            "outLinks": out_links,
            "linkCount": len(out_links),
            "lastModified": datetime.fromtimestamp(
                stat.st_mtime, tz=UTC
            ).strftime("%Y-%m-%dT%H:%M:%S"),
            "sizeBytes": stat.st_size,
            "summary": _extract_summary(text),
            "preview": _extract_preview(text),
            "inboundLinks": [],
            "inboundCount": 0,
        }

        if fm.get("project"):
            note["project"] = str(fm["project"])
        if fm.get("priority"):
            note["priority"] = str(fm["priority"])
        if fm.get("parent"):
            note["parent"] = str(fm["parent"])

        notes[rel_path] = note

        for target in out_links:
            inbound_links.setdefault(target, []).append(stem)

        for tag in tags:
            tag_index.setdefault(tag, []).append(rel_path)
        if note["domain"]:
            domain_index.setdefault(note["domain"], []).append(rel_path)
        if note["status"]:
            status_index.setdefault(note["status"], []).append(rel_path)
        if note["type"]:
            type_index.setdefault(note["type"], []).append(rel_path)
        for kw in keywords:
            keyword_index.setdefault(kw, []).append(rel_path)

    for note in notes.values():
        inbound = sorted(set(inbound_links.get(note["basename"], [])))
        note["inboundLinks"] = inbound
        note["inboundCount"] = len(inbound)

    total_notes = len(notes)
    total_links = sum(n["linkCount"] for n in notes.values())
    orphan_count = sum(
        1 for n in notes.values()
        if n["inboundCount"] == 0 and not is_system_note(n["path"])
    )
    avg_links = round(total_links / total_notes * 10) / 10 if total_notes > 0 else 0

    para_dist: dict[str, int] = {}
    for n in notes.values():
        para_dist[n["paraFolder"]] = para_dist.get(n["paraFolder"], 0) + 1

    status_dist: dict[str, int] = {k: len(v) for k, v in status_index.items()}

    stats: dict[str, Any] = {
        "totalNotes": total_notes,
        "totalLinks": total_links,
        "avgLinksPerNote": avg_links,
        "orphanNotes": orphan_count,
        "uniqueTags": len(tag_index),
        "uniqueKeywords": len(keyword_index),
        "domains": sorted(domain_index.keys()),
        "paraDistribution": para_dist,
        "statusDistribution": status_dist,
    }

    notes_array = sorted(notes.values(), key=lambda n: n["path"])

    return {
        "version": "2.0",
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "vault_path": str(vault_path).replace("\\", "/"),
        "note_count": total_notes,
        "stats": stats,
        "notes": notes_array,
        "noteIndex": notes,
        "tagIndex": tag_index,
        "domainIndex": domain_index,
        "statusIndex": status_index,
        "typeIndex": type_index,
        "keywordIndex": keyword_index,
    }


def build_and_write_manifest(vault_path: Path) -> str:
    manifest = build_manifest(vault_path)
    manifest_path = vault_path / "_meta" / "vault-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(tmp, manifest_path)

    stats = manifest["stats"]
    return (
        f"Manifest built: {manifest['note_count']} notes -> {manifest_path}\n"
        f"  Links: {stats['totalLinks']} | Keywords: {stats['uniqueKeywords']}"
        f" | Orphans: {stats['orphanNotes']}"
    )
