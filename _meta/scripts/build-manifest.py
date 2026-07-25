#!/usr/bin/env python3
"""Build vault-manifest.json from all markdown files in the Obsidian vault.

Produces a rich index matching the MCP manifest builder:
- Per-note metadata with frontmatter, links, previews
- Keyword index (significant words → note paths)
- Tag, domain, status, type indexes (O(1) lookups)
- Inbound/outbound link graph
- Summary statistics (orphans, PARA distribution, link density)
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

VAULT_PATH = os.environ.get("VAULT_PATH", str(Path(__file__).resolve().parents[2]))
EXCLUDE_DIRS = {".git", ".obsidian", "_templates", "node_modules", ".claude", ".trash"}
MANIFEST_PATH = os.path.join(VAULT_PATH, "_meta", "vault-manifest.json")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")

# --- Stop words (common English words to exclude from keyword index) ---
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

MIN_KEYWORD_LENGTH = 4
PREVIEW_LENGTH = 500
KEYWORD_RE = re.compile(r"[a-z]{4,}")


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown text."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    try:
        fm = yaml.safe_load(text[3:end])
        return fm if isinstance(fm, dict) else {}
    except yaml.YAMLError:
        return {}


def extract_title(text: str, stem: str) -> str:
    """Extract first H1 heading or fall back to filename stem."""
    m = re.search(r"(?m)^#\s+(.+)$", text)
    return m.group(1).strip() if m else stem


def extract_summary(text: str, max_len: int = 150) -> str:
    """Extract first meaningful paragraph as summary."""
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:]

    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">") or line.startswith("---"):
            continue
        if line.startswith("[[") or line.startswith("- ["):
            continue
        summary = line[:max_len]
        if len(line) > max_len:
            summary = summary.rsplit(" ", 1)[0] + "..."
        return summary
    return ""


def extract_preview(text: str, length: int = PREVIEW_LENGTH) -> str:
    """Extract first N chars of body content (after frontmatter)."""
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:]
    body = body.strip()
    if len(body) > length:
        return body[:length] + "..."
    return body


def extract_links(text: str) -> list[str]:
    """Extract all [[wikilinks]] from text, returning basenames."""
    targets = set()
    for m in WIKILINK_RE.finditer(text):
        raw = m.group(1).strip()
        # Get just the note name (strip path prefixes)
        name = raw.split("/")[-1]
        # Only strip .md extension — Path.stem strips ANY extension,
        # which breaks names like "v1.7" (treats ".7" as extension)
        if name.endswith(".md"):
            name = name[:-3]
        targets.add(name)
    return sorted(targets)


def extract_keywords(title: str, body_snippet: str) -> list[str]:
    """Extract significant keywords from title + body snippet."""
    source = (title + " " + body_snippet).lower()
    words = set(KEYWORD_RE.findall(source))
    return sorted(w for w in words if w not in STOP_WORDS)


def detect_para_folder(rel_path: str) -> str:
    """Determine PARA folder from relative path."""
    m = re.match(r"^(\d\d-\w+)", rel_path)
    if m:
        return m.group(1)
    m = re.match(r"^(memory|_meta|_templates|50-maps)", rel_path)
    if m:
        return m.group(1)
    return "other"


def build_manifest() -> dict:
    """Walk vault and build the rich manifest/index."""
    vault = Path(VAULT_PATH)
    notes = {}          # path -> note metadata
    tag_index = defaultdict(list)
    domain_index = defaultdict(list)
    status_index = defaultdict(list)
    type_index = defaultdict(list)
    keyword_index = defaultdict(list)
    inbound_links = defaultdict(list)  # basename -> [source basenames]

    md_files = sorted(vault.rglob("*.md"))

    for md_file in md_files:
        rel = md_file.relative_to(vault)
        parts = rel.parts
        if any(p in EXCLUDE_DIRS or p.startswith(".") for p in parts):
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = str(rel).replace("\\", "/")
        fm = parse_frontmatter(text)
        stat = md_file.stat()
        stem = md_file.stem
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

        # Normalize tags
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        tags = [t.lstrip("#") for t in tags if t]

        title = extract_title(text, stem)
        out_links = extract_links(text)
        # Remove self-links
        out_links = [l for l in out_links if l != stem]

        # Body snippet for keywords
        body = text
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                body = text[end + 3:]
        body_snippet = body[:200] if body else ""

        keywords = extract_keywords(title, body_snippet)
        para_folder = detect_para_folder(rel_path)

        note = {
            "path": rel_path,
            "title": title,
            "basename": stem,
            "paraFolder": para_folder,
            "created": str(fm.get("created", mtime)),
            "updated": str(fm.get("updated", mtime)),
            "status": fm.get("status", ""),
            "type": fm.get("type", ""),
            "domain": fm.get("domain", ""),
            "tags": tags,
            "outLinks": out_links,
            "linkCount": len(out_links),
            "lastModified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%dT%H:%M:%S"),
            "sizeBytes": stat.st_size,
            "summary": extract_summary(text),
            "preview": extract_preview(text),
        }

        # Optional fields
        if fm.get("project"):
            note["project"] = str(fm["project"])
        if fm.get("priority"):
            note["priority"] = str(fm["priority"])
        if fm.get("parent"):
            note["parent"] = str(fm["parent"])

        notes[rel_path] = note

        # Build link graph (outbound → inbound)
        for target in out_links:
            inbound_links[target].append(stem)

        # Populate indexes
        for tag in tags:
            tag_index[tag].append(rel_path)
        if note["domain"]:
            domain_index[note["domain"]].append(rel_path)
        if note["status"]:
            status_index[note["status"]].append(rel_path)
        if note["type"]:
            type_index[note["type"]].append(rel_path)
        for kw in keywords:
            keyword_index[kw].append(rel_path)

    # Add inbound link data to each note
    for path, note in notes.items():
        bn = note["basename"]
        inbound = sorted(set(inbound_links.get(bn, [])))
        note["inboundLinks"] = inbound
        note["inboundCount"] = len(inbound)

    # Compute summary stats
    total_notes = len(notes)
    total_links = sum(n["linkCount"] for n in notes.values())
    ORPHAN_EXCLUDE_PATHS = ("/references/",)
    orphan_count = sum(
        1 for n in notes.values()
        if n["inboundCount"] == 0
        and n["paraFolder"] != "_templates"
        and not any(ex in n["path"] for ex in ORPHAN_EXCLUDE_PATHS)
    )
    avg_links = round(total_links / total_notes, 1) if total_notes > 0 else 0

    para_dist = defaultdict(int)
    for n in notes.values():
        para_dist[n["paraFolder"]] += 1

    status_dist = {k: len(v) for k, v in status_index.items()}

    stats = {
        "totalNotes": total_notes,
        "totalLinks": total_links,
        "avgLinksPerNote": avg_links,
        "orphanNotes": orphan_count,
        "uniqueTags": len(tag_index),
        "uniqueKeywords": len(keyword_index),
        "domains": sorted(domain_index.keys()),
        "paraDistribution": dict(para_dist),
        "statusDistribution": status_dist,
    }

    # Build the legacy "notes" array for backward compatibility
    notes_array = sorted(notes.values(), key=lambda n: n["path"])

    return {
        "version": "2.0",
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "vault_path": str(vault).replace("\\", "/"),
        "note_count": total_notes,
        "stats": stats,
        # Legacy flat array (used by existing vault_search, vault_recent, etc.)
        "notes": notes_array,
        # Rich indexes
        "noteIndex": dict(notes),
        "tagIndex": dict(tag_index),
        "domainIndex": dict(domain_index),
        "statusIndex": dict(status_index),
        "typeIndex": dict(type_index),
        "keywordIndex": dict(keyword_index),
    }


def main():
    manifest = build_manifest()
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Manifest built: {manifest['note_count']} notes -> {MANIFEST_PATH}")
    print(f"  Links: {manifest['stats']['totalLinks']} | Keywords: {manifest['stats']['uniqueKeywords']} | Orphans: {manifest['stats']['orphanNotes']}")


if __name__ == "__main__":
    main()
