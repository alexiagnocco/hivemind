---
name: health-check
description: Quick hive health scan checking for orphan notes, broken links, missing frontmatter, and stale content. Use for fast daily or session-start diagnostics.
allowed-tools: Read, Glob, Grep, Bash(find *), Bash(wc *)
---

# Hive Health Check

Fast diagnostic scan. Read `_meta/hive-health.md` for the last check date, then scan and update.

## Checks (run all)

Use `hive_manifest()` to load the full hive index for metadata-based checks (orphans, staleness, missing frontmatter, tags). Use `hive_read()` only when you need to inspect specific note content. This replaces manual Glob/Grep scanning.

1. **Inbox count**: How many notes in `00-inbox/`? Flag if >10. (Count manifest entries with path starting `00-inbox/`.)
2. **Orphan notes**: Notes with zero inbound links (exclude inbox, templates, meta). (Use manifest `links` field to build a link graph.)
3. **Broken links**: `[[wiki-links]]` pointing to nonexistent files. (Compare manifest `links` against known titles.)
4. **Missing frontmatter**: Notes missing required YAML fields per CLAUDE.md schema. (Check manifest fields for empty values.)
5. **Stale notes**: Notes in `10-projects/` or `20-areas/` not modified in 30+ days. (Compare manifest `updated` field to today.)
6. **Empty notes**: Files with <50 characters of content body. (Check manifest `summary` field — empty summary suggests empty note.)
7. **Stale serialized queries**: MOCs in `50-maps/` containing `<!-- SerializedQuery:` or `<!-- SerializedDataviewJS -->` markers where the file's `git log -1` or `file.mtime` is older than 7 days. This means Obsidian hasn't refreshed the Dataview results recently. Flag with: "Serialized Dataview results may be stale — open [file] in Obsidian to refresh."

## Output

Update `_meta/hive-health.md` with:

```markdown
# Hive Health

Last checked: YYYY-MM-DD

## Status: [Healthy | Needs Attention | Critical]

| Metric | Count | Status |
|--------|-------|--------|
| Inbox backlog | N | OK / Warning / Critical |
| Orphan notes | N | OK / Warning |
| Broken links | N | OK / Warning |
| Missing frontmatter | N | OK / Warning |
| Stale project notes | N | OK / Warning |
| Empty notes | N | OK / Warning |
| Stale serialized queries | N | OK / Warning |

## Items Needing Attention
- [list specific files/issues if any]
```

Display a one-line summary in the terminal: "Hive health: [status]. [N] items need attention."
