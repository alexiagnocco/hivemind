---
description: YAML frontmatter schema and tag policy for all hive notes
globs: "**/*.md"
---

# Frontmatter Schema & Tag Policy

## Required Frontmatter (all notes)

```yaml
created: YYYY-MM-DD          # Date created, never modified after
updated: YYYY-MM-DD          # Last meaningful edit date — update on every edit
tags: []                      # Array of tags (see policy below)
status: draft | active | review | done | archived
type: note | project | meeting | decision | reference | moc | log
domain: work | meta            # work = engineering content; meta = system files
```

### Recognized Extension Types

In addition to the canonical types above, four extension types are used consistently by system areas and should not be flagged as drift by `/health-check`:

| Extension type | Used by | Scope |
|---|---|---|
| `readme` | `_README.md` landing pages (`00-inbox/`, `10-projects/`, `20-areas/`, etc.) | System files — describe folder purpose |
| `area` | `20-areas/<area>/<area>.md` landing pages (e.g., `reliability.md`, `code-review.md`, `on-call.md`) | PARA Area root notes |
| `feedback` | `memory/feedback_*.md` MemRL memory files | Atomic "always do X when Y" rules captured via `/feedback` |
| `review` | `_meta/reviews/` outputs (weekly-reviews, connection-scans, decision-debt reports) | Periodic review artifacts |

Do not use these extension types for regular content notes — content notes should use the canonical vocabulary.

## Optional Frontmatter (by type)

**Project notes** add:
```yaml
project: project-slug
priority: high | medium | low
due: YYYY-MM-DD              # if applicable
```

**Meeting notes** add:
```yaml
attendees: []
action-items: []
```

**Decision records** add:
```yaml
decision: accepted | rejected | superseded
context: "brief context string"
```

**Hierarchy (Breadcrumbs plugin):**
```yaml
parent: "[[50-maps/MOC-API-Design]]"
```

## Tag Policy

Tags are for **cross-cutting topics not captured by `domain`, `type`, or `status`**.

### Core vocabulary (15 tags):

| Tag             | Scope                               |
| --------------- | ----------------------------------- |
| `#backend`      | Backend services, APIs              |
| `#data`         | Data pipelines, signals, data flow  |
| `#devops`       | Build, batch, scheduling, infra     |
| `#scripting`    | Scripts, automation glue            |
| `#git`          | Version control, migration          |
| `#testing`      | Tests, eval harnesses, QA           |
| `#retrieval`    | Search, ranking, embeddings         |
| `#mcp`          | MCP servers, agent tooling          |
| `#obsidian`     | Hive, PKM, plugins                 |
| `#ai`           | AI tooling, Claude Code             |
| `#meta`         | Hive system files                  |
| `#synthesis`    | Cross-domain connection notes       |
| `#architecture` | Architectural decisions/patterns    |
| `#optimization` | Cross-cutting optimization patterns |
| `#automation`   | Scheduled tasks, scripts            |

**Do NOT use** tags that echo frontmatter: `#project`, `#meeting`, `#decision`, `#moc`, `#review`, `#work`.

## Frontmatter Editing Rules

- NEVER remove existing frontmatter fields when editing a note
- ALWAYS update the `updated:` field when making meaningful changes
- ALWAYS use ISO 8601 date format (YYYY-MM-DD)
- Wikilinks in frontmatter must be quoted: `project: "[[project-name]]"`
