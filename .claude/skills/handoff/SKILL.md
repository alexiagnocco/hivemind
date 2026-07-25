---
description: "Capture session context for continuity between sessions"
---

# /handoff — Session Continuity

Capture session state so the next session starts at Week 1, not Week 0.

## Usage

`/handoff` · `/handoff --project <slug>` · `/handoff --quick`

## Behavior

1. Review session work: files changed, decisions made, open questions
2. Identify project (ask if unclear; default to `memory/context/hive-handoff.md`)
3. **Append** to `memory/projects/<project>.md`:

```markdown
## Session Handoff — YYYY-MM-DD
### What Was Done
- Completed items with [[wikilinks]]
### Decisions Made
- Decision + rationale
### In Progress
- Partial work and current state
### Blockers / Open Questions
- Items needing resolution
### Next Session Start
- First action for next session
- Key files: [[file1]], [[file2]]
```

4. **MemRL Feedback** — Before writing the handoff:
   - Identify notes retrieved via `/recall` or `hive_retrieve` this session
   - Classify each: cited/referenced in created/edited files = helpful, surfaced but unused = not helpful
   - Call `hive_feedback` with the classified paths
   - Report: "Recorded feedback for N notes (M helpful, K not helpful)"
5. Update `updated:` on project memory file
6. Verify new notes have inbound links
7. Tell user: "Resume with `/recall --project <slug>`"

## Rules

- Always append, never overwrite
- Keep concise — next session scans in <30 seconds
- Always include "Next Session Start" (most important section)
- Don't duplicate note contents — link to them
