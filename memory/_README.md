---
created: 2026-07-11
updated: 2026-07-11
tags: [meta]
status: active
type: readme
domain: meta
---

# memory — deep agent memory

Long-lived context the agent loads before working:

- `projects/<project-slug>.md` — running project memory (decisions,
  handoffs, open questions). **Must stay flat**: the MCP server resolves
  `memory/projects/<project>.md` as an exact path
  (`hive_context`/`hive_checkpoint`/`hive_session_check`) — no
  subdirectories here.
- `context/` — durable cross-project context.
- `people/` — contact and stakeholder profiles. Keep private.
- `glossary.md` — terms and acronyms.
- `feedback_*.md` — atomic MemRL feedback rules captured via `/feedback`.

Project memory is append-only: add checkpoints and handoffs, never rewrite
history.
