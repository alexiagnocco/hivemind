---
name: boot
description: "Session startup: get date, load context, check health, and surface relevant knowledge. The counterpart to /wrap. Triggers: 'boot', 'start session', 'load context', 'what am I working on', 'session start', 'initialize', 'get oriented'."
---

# /boot — Session Startup

Boot the session with full hive awareness. This is the `/recall` + `/health` context-load combo that should run at the start of every substantive session. The counterpart to `/wrap` at session end.

## Usage

`/boot` -- auto-detect project from pwd, load everything
`/boot <topic>` -- load context for a specific topic/query
`/boot --project <slug>` -- load context for a named project

## Phases

Execute all phases without asking for confirmation. Keep output concise — this is a boot sequence, not a deep analysis. Target <60 seconds total.

### Phase 1: Timestamp

Run `date "+%A, %Y-%m-%d %I:%M %p"` and store the result. This anchors all time-relative decisions (staleness checks, deadlines, nudge cooldowns) for the session.

### Phase 2: Health Pulse

Call `hive_health` (window_days=7, stale_threshold_days=30). Display a single-line summary:

```
Health: COMPOUNDING | K=217 | sigma=0.77 | rho=0.33 | delta=0.0
```

If DECAYING, flag it prominently. If escape velocity is borderline, note it. Otherwise one line is enough.

### Phase 3: Project Context

Determine the project:
1. If `--project <slug>` provided, use that.
2. If `<topic>` provided, use it as a search query.
3. Otherwise derive from `pwd`: `basename "$(pwd)"` maps to `memory/projects/<project>.md`.

Call `hive_context` with the project/query. Display:
- **Last session**: What was done, what's pending (from project memory handoff)
- **Open questions**: Any unresolved items
- **Next action**: The "Next Session Start" item from the last `/handoff`

If no project memory exists, say so and move on.

### Phase 4: Recall

Call `hive_retrieve` with the topic/project context. Show top 5 results (not 10 — this is a quick boot, not deep research):

```
## Relevant Knowledge (5)
- [[note]] — summary (utility: 0.XX)
- ...
```

Call `hive_related` on the top 1-2 results to surface link-graph neighbors. Add any novel neighbors to the list.

Track the `retrievalId` for later `/feedback`.

### Phase 5: Inbox & Nudge Check

Quick checks (do NOT run full scans):
- Count items in `00-inbox/` — if >5, note it.
- Check manifest age — if >3 days, note it.
- Check if unmined sessions exist — if >3, note it.

Display at most ONE nudge per the nudge priority system.

### Phase 6: Ready Summary

Print a compact ready block:

```
--- Session ready ---
Date: Saturday, 2026-04-04 8:05 PM
Health: COMPOUNDING (K=217)
Project: <project> — <one-line status>
Last handoff: <date> — <next action from handoff>
Recalled: N notes (retrievalId: YYYYMMDDHHMMSS)
Nudge: <if any>
---
End session with /wrap
```

## Rules

- **Never ask for confirmation** between phases. Boot fast.
- **40% context rule** — load only what's relevant. Don't stuff context with everything.
- **One nudge max** — follow the nudge priority system.
- **Track retrievalId** — essential for `/feedback` at session end (or during `/wrap`).
- **If hivemind MCP is unavailable**, fall back to direct file reads: `memory/projects/`, `30-resources/`, `_meta/hive-manifest.json`.
- **If this is a fresh hive with no project memory**, say so honestly and suggest what to work on based on inbox and recent activity.
- **Keep total output under 40 lines** — this is a boot screen, not a report.
