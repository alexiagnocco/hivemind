---
name: weekly-review
description: Generate a "State of the Hive" assessment covering what's working, what's decaying, behavioral patterns, and specific next actions. Use weekly or biweekly.
allowed-tools: Read, Write, Glob, Grep, Bash(find *), Bash(wc *), Bash(sort *)
---

# Weekly Review — State of the Hive

> **Recommended mode: Plan.** This skill analyzes behavioral patterns, compares trends, and generates honest assessments. Plan mode produces significantly better insight here. Switch with `Shift+Tab` if needed.

Generate an honest assessment of hive health, usage patterns, and recommended changes.

## Focus Mode

The weekly review ALWAYS analyzes the full hive — this is a meta-level assessment where cross-domain visibility matters. However, in the terminal output, organize findings by domain and clearly label each section so the user can skip domains they're not focused on right now.

## Step 1: Gather Data

Use Hivemind tools for efficient data gathering:
- `hive_recent(days=7)` for all notes modified in the last week, grouped by domain
- `hive_manifest()` for full hive state (inbox count, total notes, domain distribution)
- Read `_meta/hive-health.md` for current metrics
- Read the most recent review in `_meta/reviews/` for comparison
- Identify which domains had zero activity
- Check inbox backlog trend (growing, stable, shrinking)

## Step 2: Behavioral Analysis

Analyze patterns and tendencies:

- **Capture habits**: What am I capturing? What am I NOT capturing that I should be?
- **Domain balance**: Am I over-indexing on one area (e.g., backend) and neglecting others (e.g., testing, infra)?
- **Depth vs. breadth**: Am I creating many shallow notes or fewer deep ones?
- **Follow-through**: Are notes getting enriched and linked over time, or staying as rough drafts?
- **Revisit rate**: Which notes from >2 weeks ago have been touched recently? Which haven't?

## Step 3: Structural Health

- Any MOCs that are getting too long (>50 entries) and should be split?
- Any folders that are getting too flat (>20 files) and need substructure?
- Any emerging topic clusters that deserve their own MOC?
- Any archived items that should be resurrected?

## Step 4: Write the Review

Create `_meta/reviews/YYYY-MM-DD-weekly-review.md`:

```markdown
---
created: YYYY-MM-DD
type: log
status: done
tags: [meta, review]
---

# State of the Hive — YYYY-MM-DD

## Summary
[3-4 sentence overview]

## What's Working
- [specific positives with evidence]

## What's Decaying
- [specific concerns with evidence]

## Behavioral Patterns
- [honest observations about habits, tendencies, blind spots]

## Domain Activity (Last 7 Days)
| Domain | Notes Created | Notes Modified | Trend |
|--------|--------------|----------------|-------|
| Backend | N | N | ↑ ↓ → |
| Data / Retrieval | N | N | ↑ ↓ → |
| Infra / DevOps | N | N | ↑ ↓ → |
| ... | | | |

## Recommendations
1. [specific, actionable recommendation]
2. [specific, actionable recommendation]
3. [specific, actionable recommendation]

## Open Questions
- [threads worth pulling on, unresolved items]
```

## Tone

Be direct. This review should feel like a honest performance assessment, not a cheerful summary. If I'm neglecting my health notes, say so. If my project notes are shallow, call it out. Useful friction > comfortable silence.

## Output

Display the Summary, What's Decaying, and Recommendations sections in the terminal. Save the full review to the file.
