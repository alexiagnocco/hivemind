---
description: Automatic hive integration protocol for reading and writing hive context from any project directory
---

# Hive Integration Protocol

The hive at `~/hive/` (override with the `HIVE_PATH` env var) is a persistent knowledge layer. When working in any project directory, Claude automatically consults and updates the hive without being asked.

## Automatic Hive Reads

### On Session Start

1. **Project memory**: Read ~/hive/memory/projects/<project-name>.md where <project-name> matches the current project directory name. Use `hive_read` or Read tool.
2. **Glossary**: Use `hive_search` for terms relevant to the project's domain.
3. **Context load**: Use `hive_context` MCP tool for composite pre-session loading (project memory + domain search + recent activity + inbox nudge).
4. **Recall**: The `/recall` skill orchestrates this — prefer it over manual steps.

### During Work

- **Unfamiliar term/acronym**: hive_search for the term
- **Architectural decision needed**: Search for prior ADRs, patterns, decisions
- **Before creating anything**: Check hive for existing notes on the topic
- **Before citing facts about tools, APIs, or dates**: Verify against the actual source (read the file, call the API, use a date tool). Never compute day-of-week mentally. Never assert what tools a team "uses" without checking the hive or project memory.

### Project-to-Hive Mapping

Convention: directory name maps to hive memory file.
- `~/projects/acme-api/` → `~/hive/memory/projects/acme-api.md`
- `~/projects/data-pipeline/` → `~/hive/memory/projects/data-pipeline.md`
- Fallback: hive_search by project name

### MCP Tools (hivemind)

The hivemind MCP server provides structured hive access. Prefer these over raw file reads:

| Tool | Purpose |
|------|---------|
| `hive_search` | Find notes by metadata and/or text query |
| `hive_read` | Read full content of specific notes by path |
| `hive_retrieve` | Hybrid retrieval: keyword composite (match + freshness + connectivity) fused with dense-vector cosine, then re-ranked by MemRL utility |
| `hive_recent` | Notes modified in last N days, optional domain filter |
| `hive_related` | Bidirectional link graph neighbors for a note |
| `hive_context` | Pre-session context loader (project memory + domain + recent + inbox) |
| `hive_health` | Knowledge health metrics (sigma, rho, delta, phi, escape velocity) |
| `hive_session_check` | Post-session validation (new notes, orphans, frontmatter, project memory) |
| `hive_feedback` | Record helpful/not-helpful feedback for MemRL utility scoring |
| `hive_sigma_rho` | Compute true sigma/rho from accumulated feedback data |
| `hive_rebuild` | Trigger manifest rebuild |
| `hive_unmined_sessions` | Find sessions not yet mined for knowledge |

### Token Efficiency

- Use targeted `hive_search`, not `hive_manifest`
- Never load the full manifest for project sessions
- Read frontmatter + first section, not full notes
- Lazy loading: don't fetch until needed

## Automatic Hive Writes

### When to Write

| Trigger | What to Write | Where |
|---------|--------------|-------|
| Significant decision made | Decision + rationale | ~/hive/memory/projects/<project>.md |
| Milestone completed | Status/progress update | ~/hive/memory/projects/<project>.md |
| Measurable accomplishment | Win + context + metrics | ~/hive/20-areas/accomplishments-log.md |
| New term/acronym learned | Definition | ~/hive/memory/glossary.md |
| New person encountered | Profile | ~/hive/memory/people/<name>.md |
| Reusable pattern discovered | Resource note | ~/hive/30-resources/<domain>/ or 00-inbox/ |
| Non-obvious bug root cause | Documentation | ~/hive/30-resources/<domain>/ |
| Session ending (substantive work done) | Session handoff | Use `/handoff` skill |
| Rate limit / context overflow | Session handoff | ~/hive/00-inbox/session-handoff.md |

### Write Rules

- All hive paths MUST be absolute (~/hive/...)
- Always update updated: frontmatter when modifying existing notes
- Append to existing notes for logs and project memory (never overwrite)
- Batch writes: update when something meaningful happens, not after every response

### Scope Guard

| Context | Write Behavior |
|---------|---------------|
| Working in the hive (~/hive/) | Write per hive operating rules |
| Working in a project | Decisions, milestones, learnings, new terms, accomplishments |
| Debugging / exploring | Only non-obvious patterns or root causes |
| Routine code changes | No hive write needed |

## Frontmatter for New Hive Notes

When creating hive notes from outside the hive:

```yaml
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []           # From: backend, data, devops, scripting, git, testing,
                   #   retrieval, mcp, obsidian, ai, meta, synthesis,
                   #   architecture, optimization, automation
status: active     # draft | active | review | done | archived
type: note         # note | project | meeting | decision | reference
domain: work       # work | meta
---
```

When appending to existing notes, update only the updated: field.

## Conflict Avoidance

- Write using absolute paths
- Writes are append-only for logs/memory
- If a hive file has uncommitted changes, append rather than overwrite