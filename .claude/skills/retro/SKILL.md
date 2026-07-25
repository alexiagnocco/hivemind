---
description: "Capture learnings and retrospectives from development work"
---

# /retro — Learning Capture

Persist learnings to hive before they decay. Search before creating; append to existing notes when possible.

## Quick Mode: `/retro "insight"`

1. Determine domain (backend, data, infra, devops, testing, retrieval, ai-ml, meta)
2. `hive_search` for existing notes on topic — **append** if found
3. If new note: create at `30-resources/<domain>/<slug>.md` with frontmatter (created, updated, tags, status: active, type: reference, domain), `parent:` linking to MOC, sections: Context, The Learning, Related
4. If appending: add dated section, update `updated:` field, add new [[wikilinks]]

## Full Mode: `/retro full`

1. Ask: what was done, what went well, what surprised, what to change
2. Search `memory/projects/` for project context
3. Create `30-resources/<domain>/retro-<topic>-<date>.md`
4. Sections: What Happened, What Went Well, What Surprised Us, What to Change, Extracted Learnings, Links
5. Append summary to `memory/projects/<project>.md`

## Rules

- Search before creating — deduplicate
- Append to existing > create new for small insights
- Every note must have at least one inbound [[wikilink]]
- End with Recommended Next Steps
