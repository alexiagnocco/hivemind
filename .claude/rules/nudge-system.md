---
description: Proactive suggestion system rules and trigger conditions
globs: "**/*.md"
---

# Nudge System

## Purpose
Proactively suggest hive-maintenance actions based on patterns detected during
normal interaction — so the knowledge base stays above escape velocity without
the user having to remember to maintain it.

## Nudge Format
Nudges appear as a single line at the end of a response:
`Nudge: {suggestion} — run {command} to proceed.`

## Trigger Conditions & Cooldowns

| Trigger | Nudge | Command | Cooldown |
|---------|-------|---------|----------|
| >5 items in `00-inbox/` | "Inbox is filling up ({n} items)" | file them into the PARA folders | 3 days |
| Note edited without updating `updated:` field | "Bump the updated date" | (manual) | Per note |
| 3+ notes created in same domain without a MOC link | "Consider linking these to a MOC" | `/connect` | 7 days |
| 7+ days since last weekly review | "Time for a weekly review" | `/weekly-review` | 7 days |
| 14+ days since last `/evolve` | "Hive hasn't evolved recently" | `/evolve` | 14 days |
| `_meta/hive-manifest.json` missing or >3 days old | "Manifest is stale — retrieval quality degrades without a fresh index" | `hive_rebuild` MCP tool | 3 days |
| `_meta/hive-health.md` not updated in 7+ days | "No recent health check — track sigma and delta" | `/health-check` or `hive_health` | 7 days |
| Session ends with 3+ notes created but no `/handoff` | "You created {n} notes — capture session context before it decays" | `/handoff` | Per session |
| Session starts without `/recall` on a dev task | "Starting from scratch? Check what the hive already knows" | `/recall <topic>` | Per session |
| 10+ notes created since last manifest rebuild | "Manifest is behind by {n} notes — search may miss recent work" | `hive_rebuild` MCP tool | 3 days |
| `hive_health` returns DECAYING | "Hive is below escape velocity — sigma*rho < delta/100" | `hive_health` for diagnosis | 7 days |
| 5+ orphan notes (no inbound `[[wikilinks]]`) | "Orphans decay fastest — link them to a MOC or parent" | `/connect` or `/link-repair` | 7 days |
| Project memory not updated in 14+ days for an active project | "Project memory going stale for {project}" | `/handoff --project {project}` | 14 days |
| `_meta/session-extract-manifest.json` missing or >7 days old | "Session transcripts haven't been mined — learnings decaying in chat" | `/mine-sessions` | 7 days |
| 3+ unmined sessions with `mineRecommended: true` | "You have {n} substantive sessions waiting to be mined" | `hive_unmined_sessions` MCP tool | 3 days |

## Priority Order

When multiple nudges qualify, pick the single highest-priority one:

1. **DECAYING status** (escape-velocity failure) — most urgent, knowledge is being lost
2. **Stale manifest** (missing or >3 days) — retrieval quality directly impacts sigma
3. **Session lifecycle** (no `/recall` at start, no `/handoff` at end) — prevents decay
4. **Orphan notes** (5+) — unlinked notes are invisible and decay fastest
5. **Stale project memory** (14+ days) — active project context is eroding
6. **Health check overdue** (7+ days) — can't manage what you don't measure
7. **Inbox overflow** (>5 items) — unprocessed input doesn't compound
8. **All other nudges** — weekly review, evolve, session mining

## Detection Methods

| Condition | How to Detect |
|-----------|---------------|
| Manifest age | Check `_meta/hive-manifest.json` mtime or `generated` field |
| Health check age | Check `updated:` frontmatter in `_meta/hive-health.md` |
| Escape velocity | Use `hive_health` or check `_meta/hive-manifest.json` stats |
| Orphan count | Use `hive_search` or check the health metric |
| Project memory staleness | Check `updated:` in `memory/projects/*.md` for active projects |
| `/recall` / `/handoff` usage | Track whether invoked this session |
| Transcript mining age | Check `_meta/session-extract-manifest.json` mtime |
| Unmined sessions | Count `_meta/session-log.jsonl` entries with `mineRecommended: true` not in the extract manifest |

The hivemind MCP tools provide authoritative measurement. Nudges use lightweight
detection (file age, frontmatter dates) to avoid expensive scans during normal
interaction.

## Rules

1. **Maximum ONE nudge per response** — pick the highest-priority applicable nudge.
2. Never nudge during focus mode for out-of-scope items.
3. Never repeat a suppressed nudge within its cooldown period.
4. Nudges are suggestions, not actions — never auto-execute.
5. If the user says "no nudges" or "quiet mode", suppress all nudges for the session.
6. Complete the task first, nudge at the end. The nudge is a suggestion, not a gate.
7. Respect "no." If the user declines a nudge, don't repeat it in the same session.
8. **Knowledge-health nudges take priority** over content nudges — system health enables everything else.
