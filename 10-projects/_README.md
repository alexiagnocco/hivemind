---
created: 2026-07-11
updated: 2026-07-11
tags: [meta]
status: active
type: readme
domain: meta
---

# 10-projects — active PARA projects

One subdirectory per active project, named by project slug:
`10-projects/<project-slug>/` (e.g. `10-projects/gateway-shim/`). A project's
notes, ADRs, and meeting notes all live inside its folder.

**Status lives in frontmatter, not in paths.** Queued or paused projects
keep their folder here with `status: draft` / `priority:` in the project
notes — never create `active/`, `queued/`, or `completed/` subdirectories
(paths are identity for wikilinks and embeddings; status is mutable).
Status overview: [[50-maps/MOC-Projects|MOC-Projects]].

When a project completes, move its whole folder to
`40-archive/10-projects/<project-slug>/` and update inbound links.

What does **not** belong here: reusable reference material
(`30-resources/`), ongoing responsibilities with no end date (`20-areas/`),
and per-project running memory (`memory/projects/<project>.md` — flat file,
required by the MCP server).
