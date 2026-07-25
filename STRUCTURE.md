# Structure

How an hivemind hive is organized, and how the customization layers fit together.

## The data substrate: PARA + Zettelkasten + MOCs

Notes are Markdown files with YAML frontmatter, organized [PARA](https://fortelabs.com/blog/para/)-style and threaded together with `[[wikilinks]]` and Maps of Content (MOCs).

```text
hive/
├── 00-inbox/        Unprocessed captures → triaged into the folders below
├── 10-projects/     Active projects with a defined outcome (status: active)
├── 20-areas/        Ongoing areas of responsibility (reliability, on-call, …)
├── 30-resources/    Reference material, patterns, how-tos, by domain
├── 40-archive/      Completed / deprecated (status: archived — never deleted)
├── 50-maps/         Maps of Content (MOC-*.md) — navigable indexes by domain
└── memory/          Durable memory the agent reads first
    ├── projects/    Per-project memory (decisions, handoffs, open questions)
    ├── context/     Standing context
    ├── people/      Contact / stakeholder profiles (kept private)
    └── glossary.md  Terms and acronyms
```

Two rules make the graph compound instead of rot: **nothing is deleted** (stale notes move to `40-archive/`, which keeps their links resolvable), and **nothing is an orphan** (every note links to at least one MOC or parent). Frontmatter (`created`, `updated`, `tags`, `status`, `type`, `domain`) is the metadata the retrieval engine scores against — see [`.claude/rules/frontmatter-schema.md`](.claude/rules/frontmatter-schema.md).

## The system: `_meta/`

```text
_meta/
├── mcp-server-py/   The hivemind MCP server (Python / FastMCP) — the engine
└── scripts/         Standalone hive utilities (manifest builder, session log)
```

`_meta/` holds the machinery; runtime artifacts it generates (the manifest, embedding cache, utility scores, logs) are git-ignored — they're derived, not source.

## The four customization layers: `.claude/`

These compose to make a generic AI coding agent operate the hive. Each has a non-overlapping job — the standard Claude Code layering: MCP for *access*, skills for *workflow*, hooks for *enforcement*, agents for *context isolation*.

```text
.claude/
├── skills/        21 slash-command workflows (+ an eval harness)
├── hooks/         15 lifecycle automation scripts
├── rules/         8 always-on behavioral rules
├── agents/        2 subagent definitions
└── settings.json  wires each hook to its lifecycle event
```

| Layer | Job | Example |
|---|---|---|
| **Skills** | A workflow the agent runs on demand | `/boot` loads context; `/wrap` closes the session cleanly |
| **Hooks** | An action that fires *unconditionally* at a lifecycle event | `pre-bash-hive-delete-guard.sh` blocks `rm` of an active note |
| **Rules** | A standing convention loaded into every session | `retrieval-order.md` defines how to traverse the hive |
| **Agents** | A sub-task run in its own context window | `research.md` fans out a deep read without polluting the main thread |

## How a turn flows

1. A **rule** (`retrieval-order.md`) tells the agent to anchor on project memory, then call `hive_retrieve`.
2. The **MCP server** runs hybrid retrieval and returns scored notes with a `retrievalId`.
3. The agent does the work, persisting decisions to the hive as it goes.
4. A **hook** (`post-edit-activity-log.sh`) records each write.
5. At session end, a **skill** (`/wrap`) records `hive_feedback` for the notes that were actually cited, updates project memory, and commits — feeding the MemRL loop that sharpens the next session's retrieval.

## Repo infrastructure: `docs/` and `.github/`

Beyond the system itself, the repository ships two supporting trees:

```text
docs/                The documentation website — a bespoke static site
                     (HTML/CSS/JS), deployed to GitHub Pages.
.github/workflows/   CI (ruff + pytest + mypy) and the Pages deploy.
```

These are project infrastructure, not part of the hivemind runtime — the engine works with neither present.
