---
name: prune
description: "Archive stale notes, clean completed items, and maintain hive scale — the remediation half of /health-check"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(mv *), Bash(find *)
---

# Prune

> **Recommended mode: Plan.** Pruning touches multiple files and benefits from seeing the full candidate list before acting. Switch with `Shift+Tab` if you're not in plan mode.

Archive stale notes, clean completed items, and maintain hive scale. This is the remediation counterpart to `/health-check` — health-check detects problems, prune fixes them. Implements Phase 4 ("Scale Management") of the knowledge-compounding workflow.

**Core rule: Never delete notes.** All pruning moves notes to `40-archive/` with `status: archived`.

## Usage

- `/prune` — full scan and interactive pruning
- `/prune --stale` — focus on notes not updated in 30+ days
- `/prune --completed` — focus on projects/items with `status: done`
- `/prune --dry-run` — report what would be pruned without making changes

## Protected Locations (always skip)

These folders are exempt from pruning — they are ongoing, structural, or persistent by design:

- `20-areas/` — areas of responsibility are ongoing by definition
- `50-maps/` — MOCs are structural navigation aids
- `memory/` — persistent cross-session context
- `_meta/` — system files (health, logs, manifests)
- `_templates/` — note templates
- `40-archive/` — already archived

## Step 1: Identify Candidates

Use `hive_manifest()` to load the full hive index. Scan for pruning candidates in eligible locations (`00-inbox/`, `10-projects/`, `30-resources/`):

### Stale Notes
- Notes with `updated:` field >30 days old in `10-projects/` and `30-resources/`
- Compare manifest `updated` field against today's date
- Flag with days-since-update count

### Completed Projects
- Notes with `status: done` or `status: archived` still sitting in `10-projects/`
- These should have been moved to `40-archive/` already

### Superseded Decisions
- Notes with `decision: superseded` in frontmatter
- Notes explicitly marked as replaced by a newer version

### Empty Notes
- Files with frontmatter only and no meaningful body content
- Check manifest `summary` field — empty or near-empty suggests an empty note
- Confirm by reading the file before flagging

### Orphan System Artifacts
- Old proposal files in `_meta/` (status: `accepted` or `rejected`, >14 days old)
- Stale session handoffs in `00-inbox/` (>7 days old)
- Processed inbox items that weren't cleaned up

## Step 2: Classify Actions

For each candidate, determine the appropriate action:

| Action | When | What Happens |
|--------|------|--------------|
| **Archive** | Note is done, superseded, or no longer active | Move to `40-archive/`, set `status: archived`, bump `updated:` |
| **Keep** | Note is stale but still relevant | Update `updated:` to today (resets staleness clock) |
| **Merge** | Content belongs in another note | Flag source and target for manual merge — never auto-merge |
| **Skip** | False positive or protected note | Leave unchanged |

## Step 3: Present Candidates

If `--dry-run`, list all candidates with their recommended action and stop.

Otherwise, present one candidate at a time with full context:

```
[1/N] flaky-retry-bug.md
Location: 30-resources/backend/ | Last updated: 2026-03-10 (31 days ago)
Status: active | Domain: work | Inbound links: 2
Recommended: Archive — no updates in 31 days, low link activity
Action: Archive (a), Keep (k), Merge (m), Skip (s)?
```

**Batch mode:** If the user responds with "archive all stale" or similar, apply the recommended action to all remaining candidates of that type without further prompts. Confirm the batch count before executing: "Will archive N stale notes. Proceed?"

**Propose before executing:** If the total actions will touch >3 files, present the full plan and wait for approval before making any changes. This is a hive operating rule.

## Step 4: Execute Decisions

### Archive
1. Move file from current location to `40-archive/`
2. Update frontmatter: set `status: archived`, update `updated:` to today
3. Check for MOC references — if the note is listed in a MOC table in `50-maps/`, update that MOC entry (add "(archived)" or remove the row, per user preference)
4. Check inbound wikilinks — if >3 notes link to this file, warn the user rather than silently updating all of them

### Keep
1. Update `updated:` field to today's date
2. This explicitly resets the staleness clock — the note won't appear in the next prune scan for 30 days

### Merge
1. Log the merge candidate: source note, suggested target note, and reason
2. Do NOT move or modify either file — merging requires human judgment
3. Add to the prune summary as "flagged for manual merge"

### Skip
1. No changes — note is excluded from this prune cycle

## Step 5: Post-Prune Cleanup

After all decisions are executed:

1. **Update MOCs**: Scan `50-maps/` for any MOC that referenced moved notes. Update or annotate stale references.
2. **Log actions**: Append a summary to `_meta/architecture-log.md` with today's date:
   ```markdown
   ## Prune — YYYY-MM-DD

   - Archived: N notes (list paths)
   - Kept (clock reset): N notes
   - Flagged for merge: N notes
   - Skipped: N notes
   ```
3. **Rebuild manifest**: Run `python _meta/scripts/build-manifest.py` to update the hive index after moves.

## Step 6: Report

Display a terminal summary:

```
## Prune Summary

- Scanned: N eligible notes
- Archived: N notes (moved to 40-archive/)
- Kept (clock reset): N notes
- Flagged for merge: N notes
- Skipped: N notes

### Archived Notes
- flaky-retry-bug.md → 40-archive/
- old-pipeline-notes.md → 40-archive/

### Flagged for Manual Merge
- draft-caching-guide.md → merge into caching-guide.md
```

## Focus Mode

Scan ALL eligible locations regardless of focus mode (pruning is a hive-wide maintenance task, like `/health-check`). When reporting results, highlight items in the active focus domain first. Summarize out-of-focus items as a count: "Also found N candidates outside your current focus."

## Rules

- **Never delete notes** — only move to `40-archive/`
- **Never auto-merge** — flag merge candidates for human review
- **Show context before every decision** — last updated, link count, location, recommended action
- **Present one candidate at a time** unless user requests batch mode
- **Respect the >3 file rule** — propose before executing bulk changes
- **Update inbound links** when moving files, or warn if too many (>3) to update safely
- **Skip protected locations** — `20-areas/`, `50-maps/`, `memory/`, `_meta/`, `_templates/`, `40-archive/`
- **Log everything** — all prune actions go in `_meta/architecture-log.md`
- **Rebuild manifest after moves** — stale indexes degrade retrieval quality
