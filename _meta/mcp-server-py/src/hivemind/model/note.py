from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Note:
    path: str = ""
    title: str = ""
    basename: str = ""
    created: str = ""
    updated: str = ""
    status: str = ""
    type: str = ""
    domain: str = ""
    tags: list[str] = field(default_factory=list)
    outLinks: list[str] = field(default_factory=list)
    inboundLinks: list[str] = field(default_factory=list)
    inboundCount: int = 0
    linkCount: int = 0
    lastModified: str = ""
    sizeBytes: int = 0
    summary: str = ""
    preview: str = ""
    project: str | None = None
    priority: str | None = None
    parent: str | None = None
    paraFolder: str = ""


@dataclass
class SlimNote:
    path: str = ""
    title: str = ""
    updated: str = ""
    domain: str = ""
    status: str = ""
    type: str = ""
    tags: list[str] = field(default_factory=list)


def slim_note(n: Note) -> SlimNote:
    return SlimNote(
        path=n.path,
        title=n.title,
        updated=n.updated,
        domain=n.domain,
        status=n.status,
        type=n.type,
        tags=list(n.tags),
    )


@dataclass
class Manifest:
    version: str = ""
    generated: str = ""
    hive_path: str = ""
    note_count: int = 0
    notes: list[Note] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def note_to_dict(n: Note) -> dict[str, Any]:
    d: dict[str, Any] = {
        "path": n.path,
        "title": n.title,
        "basename": n.basename,
        "created": n.created,
        "updated": n.updated,
        "status": n.status,
        "type": n.type,
        "domain": n.domain,
        "tags": n.tags,
        "outLinks": n.outLinks,
        "inboundLinks": n.inboundLinks,
        "inboundCount": n.inboundCount,
        "linkCount": n.linkCount,
        "lastModified": n.lastModified,
        "sizeBytes": n.sizeBytes,
        "summary": n.summary,
        "preview": n.preview,
        "paraFolder": n.paraFolder,
    }
    if n.project is not None:
        d["project"] = n.project
    if n.priority is not None:
        d["priority"] = n.priority
    if n.parent is not None:
        d["parent"] = n.parent
    return d


def slim_note_to_dict(s: SlimNote) -> dict[str, Any]:
    return {
        "path": s.path,
        "title": s.title,
        "updated": s.updated,
        "domain": s.domain,
        "status": s.status,
        "type": s.type,
        "tags": s.tags,
    }


def dict_to_note(d: dict[str, Any]) -> Note:
    return Note(
        path=d.get("path", ""),
        title=d.get("title", ""),
        basename=d.get("basename", ""),
        created=d.get("created", ""),
        updated=d.get("updated", ""),
        status=d.get("status", ""),
        type=d.get("type", ""),
        domain=d.get("domain", ""),
        tags=d.get("tags", []),
        outLinks=d.get("outLinks", []),
        inboundLinks=d.get("inboundLinks", []),
        inboundCount=d.get("inboundCount", 0),
        linkCount=d.get("linkCount", 0),
        lastModified=d.get("lastModified", ""),
        sizeBytes=d.get("sizeBytes", 0),
        summary=d.get("summary", ""),
        preview=d.get("preview", ""),
        project=d.get("project"),
        priority=d.get("priority"),
        parent=d.get("parent"),
        paraFolder=d.get("paraFolder", ""),
    )
