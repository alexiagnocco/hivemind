# Operating Instructions — hivemind

This file governs how Claude Code operates inside a hivemind knowledge hive. It is methodology only — no metrics, scan outputs, or data that goes stale (those come from the `hivemind` MCP tools at run time).

## What this is

A knowledge-compounding system for engineering work. The hive is a PARA-organized store of Markdown notes linked into one organism; the `hivemind` MCP server gives structured, scored access to it; skills, hooks, and rules make the agent retrieve before acting, persist as it works, and learn what was useful. The goal is *escape velocity* — surfacing the right knowledge faster than it decays (`σ·ρ > δ/100`). *(This compounding model is adapted from [AgentOps · The Science](https://boshu2.github.io/agentops/the-science/); see [CREDITS.md](CREDITS.md).)*

## The lore (naming map)

The system is themed after the hive mind of Stranger Things — one shared
network linking every note into a single superorganism. The names are lore;
the referents are real components:

| Lore | Component |
|---|---|
| **The Hive** | The knowledge base itself — every note, one organism |
| **Vecna** | The MCP server: the central intelligence orchestrating every node |
| **The Vines** | The `[[wikilink]]` graph connecting everything |
| **The Void** | Retrieval (`hive_retrieve`) — finding anything from the dark |
| **Eleven** | The MemRL learning loop — psychic targeting that improves with feedback |
| **The Christmas Lights** | The nudge system — messages surfacing from the other side |
| **Project NINA** | `/mine-sessions` — recovering memories from past sessions |
| **The Party** | Subagent fan-out |
| **The Creel House** | `40-archive/` — where old memories live on |
| **The Gate** | `/boot` opens it; `/wrap` closes it |
| **The Upside Down** | Where orphan notes drift — unlinked, invisible, decaying |

## Non-negotiables

1. **Retrieve before you create.** Before writing a note, making a decision, or starting non-trivial work, search the hive (`hive_retrieve` / `hive_search` or `/recall`). Never start from a blank slate when the hive already knows something.
2. **Persist as you work.** Significant decisions, rationale, rejected alternatives, blockers, and non-obvious fixes go into the hive *as they happen* — not only at the end.
3. **Capture the feedback signal.** When retrieved notes are used, record it (`hive_feedback`). This is the training signal that sharpens future retrieval; skipping it lets the ranker go stale.
4. **Verify before asserting.** Don't compute dates mentally, guess an API's shape, or claim what a tool does without checking the source. A ten-second verification beats a confident error.

## Session protocol

- **Start:** `/boot` — date, health pulse, project context, and a recall pass in one command (open the Gate).
- **End:** `/wrap` — retro, feedback, session-check, handoff, and commit in one command (close the Gate).

## Response conventions

- Reference other notes with Obsidian `[[wikilinks]]`.
- Every substantive piece of knowledge lands in a hive `.md` file, not just the chat.
- End task responses with a short **Recommended Next Steps** section.

## Where knowledge goes

| Knowledge type | Destination |
|---|---|
| Reusable pattern / technique | `30-resources/<domain>/` |
| Project-specific decision | `memory/projects/<project>.md` |
| Cross-domain insight | `30-resources/synthesis/` |
| Bug fix / non-obvious workaround | `30-resources/<domain>/` or the project note |
| Raw capture to triage later | `00-inbox/` |

## The hivemind MCP tools

Prefer these over raw file reads:

| Tool | Purpose |
|---|---|
| `hive_retrieve` | Hybrid keyword + dense retrieval (RRF fusion), re-ranked by MemRL utility; `granularity: chunk` for section-anchored hits |
| `hive_search` | Metadata + text query |
| `hive_read` | Read full note content by path |
| `hive_related` | Bidirectional link-graph neighbors |
| `hive_context` | One-shot pre-session context pack: project memory + scored hits + neighbors + retrievalId |
| `hive_feedback` | Record retrieval helpfulness (the MemRL signal) |
| `hive_health` / `hive_sigma_rho` | Knowledge-health metrics; measured σ/ρ |
| `hive_rebuild` | Rebuild the manifest index and pre-warm the retrieval indexes |

List tools accept `detail: minimal|standard|full` to size their responses.
`HIVEMIND_PROFILE=lean` registers only the 8 core tools for token-metered
clients; `full` (default) registers all 23.

## Modular rules

Detailed conventions live in `.claude/rules/` and load automatically:

- `hive-architecture.md` — folder structure, naming, linking
- `frontmatter-schema.md` — YAML frontmatter + tag policy
- `knowledge-workflow.md` — the retrieve → persist → extract lifecycle
- `retrieval-order.md` — how to traverse the hive for context
- `nudge-system.md` — proactive maintenance suggestions (the Christmas Lights)
- `skills.md` — the slash-command reference
- `subagent-patterns.md` — when and how to fan out to the Party
- `hive-integration.md` — auto read/write protocol from any project directory

## Operating rules

1. Never delete notes — archive to `40-archive/` (the Creel House) to preserve the link graph.
2. Always bump the `updated:` field when editing a note.
3. Append to logs and project memory; never overwrite.
4. No orphans — every note should have at least one inbound link (nothing left in the Upside Down).
5. CLAUDE.md holds methodology, never data — data comes from tools at run time.
