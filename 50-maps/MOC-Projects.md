---
created: 2026-07-11
updated: 2026-07-11
tags: [meta]
status: active
type: moc
domain: work
---

# MOC — Projects

Map of all PARA projects. Lifecycle status lives in each note's `status:` /
`priority:` frontmatter — never in folder paths (paths are identity for
wikilinks and embeddings; mutable state in a path forces link-breaking
moves) — so this dashboard is the status view of `10-projects/`.

## Active projects

- [[gateway-shim-consolidation|gateway-shim]] — consolidate every MCP server
  behind one gateway shim. Decisions: [[ADR-001-mcp-gateway-shim]].
- [[agent-eval-harness-buildout|agent-eval-harness]] — graded eval suite and
  CI gating for agent changes. Decisions: [[ADR-002-eval-gating-in-ci]],
  [[ADR-003-agent-job-checkpointing]].

## Status dashboard

Serialized Dataview (updates when this file is opened or saved in Obsidian;
for real-time state during Claude Code sessions prefer `hive_search`):

<!-- QueryToSerialize: TABLE status, priority, updated FROM "10-projects" WHERE type != "readme" SORT status ASC, updated DESC -->
<!-- SerializedQuery: TABLE status, priority, updated FROM "10-projects" WHERE type != "readme" SORT status ASC, updated DESC -->
<!-- SerializedQuery END -->

## Conventions

- One folder per project: `10-projects/<project-slug>/` — see
  [[10-projects/_README|the 10-projects landing page]].
- Completed projects move wholesale to `40-archive/10-projects/<slug>/`.
- Running memory stays in `memory/projects/<project>.md` (flat, append-only).
