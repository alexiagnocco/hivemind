---
created: 2026-07-11
updated: 2026-07-11
tags: [meta]
status: active
type: readme
domain: meta
---

# 40-archive — completed and deprecated

Notes are never deleted — they move here so the link graph stays intact.
**Mirror the source path** on archival: a completed project folder
`10-projects/<slug>/` becomes `40-archive/10-projects/<slug>/`, a stale
resource `30-resources/backend/x.md` becomes
`40-archive/30-resources/backend/x.md`. Provenance survives, and
un-archiving is a mechanical reverse move.

Set `status: archived` in frontmatter and update inbound links when moving.
The server treats everything under this prefix as archived at any depth;
archived notes are excluded from retrieval unless explicitly requested.
