---
description: "Find and extract knowledge from unmined Claude Code sessions"
---

# /mine-sessions — Session Knowledge Extraction

Surface sessions that contain unextracted knowledge, then mine them.

## Usage

`/mine-sessions` · `/mine-sessions --extract`

## Behavior

1. **Discover** — Call `hive_unmined_sessions` to find sessions with `mineRecommended: true` that haven't been processed.
2. **Report** — Show each unmined session: date, project, duration, topic summary, why it's worth mining.
3. **Extract** (if `--extract` or user confirms):
   - For each session, identify: decisions made, patterns learned, gotchas discovered, reusable techniques.
   - Search hive first (`hive_search`) for existing notes on each topic — append to existing notes when possible.
   - Create new notes in `30-resources/<domain>/` for genuinely new learnings.
   - Update `memory/projects/<project>.md` with any project-specific context.
   - Mark sessions as mined in `_meta/session-extract-manifest.json`.
4. **Summary** — Report: sessions processed, notes created/updated, topics covered.

## Output

All extracted knowledge persists to hive notes. Session processing metadata goes to `_meta/session-extract-manifest.json`.

## MCP Tool

Primary: `hive_unmined_sessions`
Supporting: `hive_search`, `hive_read`, `hive_feedback`
