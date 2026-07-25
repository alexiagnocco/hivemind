---
name: link-repair
description: "Fix broken wikilinks, link orphan notes to MOCs, and repair escape-character bugs in hive notes"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python *)
---

# /link-repair — Broken Link & Orphan Remediation

Scan the hive for broken wikilinks, orphan notes, and escape-character bugs, then fix them interactively. This is the remediation counterpart to `/health-check`, which detects but doesn't repair.

## Usage

- `/link-repair` — full scan and interactive repair (all issue types)
- `/link-repair --orphans` — focus on orphan notes only
- `/link-repair --broken` — focus on broken wikilinks only
- `/link-repair --dry-run` — report what would be fixed without making changes

## Procedure

### Step 1: Build the File Index

Use Glob to collect all `.md` files in the hive. Build two lookup structures:

- **Path set**: All `.md` file paths (for existence checks)
- **Name map**: Lowercase filename (without `.md`) → full path (for fuzzy matching)

**Exclusions for the file index**: Skip files in `40-archive/`, `_templates/`, `_meta/scripts/`, `_meta/mcp-server-py/`, and any `SKILL.md` or `README.md` files outside the main hive content folders. These are system/archived notes that don't need repair.

### Step 2: Scan for Broken Wikilinks

Use Grep to find all `[[wikilinks]]` across hive `.md` files. Apply these **source file exclusions** — these files are historical records or system-generated and their broken links are expected/intentional:

**Skip scanning these source files entirely:**
- `40-archive/` — archived notes, stale references are expected
- `_meta/hive-audit-*.md` — point-in-time audit snapshots with pre-reorg naming
- `_meta/hive-maintenance*.md` — historical maintenance reports
- `_meta/hive-evolution-log.md` — evolution run history with template examples
- `_meta/inbox/daily-triage-*.md` — auto-generated daily triage logs
- `_meta/reviews/*-connection-scan*.md` — auto-generated connection scan reports
- `_meta/CLAUDE-md-update-proposal-*.md` — evolution proposals with example syntax
- `EXAMPLES.md` — example syntax file

**Skip these link targets as non-content (they live in `.claude/` not the hive):**
- Skill names: `[[boot]]`, `[[recall]]`, `[[evolve]]`, `[[frame]]`, and any other `.claude/skills/` name
- Rule names: `[[frontmatter-schema]]`, `[[skills]]`, `[[wiki-links]]`, `[[wikilinks]]`

**Skip these link patterns as template/example placeholders:**
- Targets starting with `path/` or containing `{{`
- Targets like `[[note-a]]`, `[[note-b]]`, `[[existing-note]]`, `[[topic]]`, `[[project-name]]`
- Targets referencing old pre-reorg numbered folders (`[[0 Inbox]]`, `[[1 Projects/...]]`, `[[2 Areas/...]]`, etc.)
- Targets matching `[[Article*.md]]` or `[[${...}]]` (Dataview template variables)

After exclusions, for each remaining link:

1. Extract the target name (strip `#section` anchors and `|alias` suffixes)
2. Check if the target exists in the name map (case-insensitive)
3. If not found, classify as a **broken link**

For each broken link, attempt near-match resolution:

- **Case mismatch**: `[[api-design]]` vs file `API-Design.md`
- **Hyphen variance**: `[[batch processing]]` vs file `batch-processing.md`
- **Partial match**: `[[api-design]]` vs file `api-design-guide.md`
- **Plural/singular**: `[[pipelines]]` vs file `pipeline.md`

Classify each broken link:

| Match Quality | Action |
|---|---|
| Single exact match (case-insensitive) | Auto-fixable — propose direct replacement |
| Single near-match (edit distance ≤ 2) | Auto-fixable — propose with high confidence |
| Multiple near-matches | Needs judgment — show options, ask user to choose |
| No match found | Flag for manual review — target may need to be created |

### Step 3: Scan for Orphan Notes

An orphan note has **zero inbound wikilinks** from any other note. Build an inbound-link count by scanning all wikilinks collected in Step 2.

For each orphan note:

1. Read its frontmatter (`domain`, `tags`, `type`) and first heading
2. Skip notes that are inherently standalone: MOCs themselves, `memory/glossary.md`, log files
3. Identify the best-fit MOC from `50-maps/MOC-*.md` by matching:
   - `domain` frontmatter alignment
   - Tag overlap with the MOC's scope
   - Folder proximity (same domain subtree)
4. If a clear MOC match exists, propose adding `- [[note-name]]` to that MOC
5. If multiple MOCs could fit, show options and ask the user to choose
6. If no MOC fits, suggest creating a link from a related note instead

### Step 4: Scan for Escape-Character Bugs

Search for common escape and formatting issues in wikilinks:

1. **Wikilinks with `.md` extension**: `[[note-name.md]]` should be `[[note-name]]`
2. **Unmatched brackets**: Lone `]]` without opening `[[`, or vice versa
3. **Pipe inside Dataview queries**: `|` characters inside `[[link|alias]]` within ` ```dataview` blocks that may break table rendering — flag but don't auto-fix (Dataview syntax is fragile)
4. **Double-bracket collisions**: `[[ [[nested]] ]]` or `]]]]` bracket pileups

### Step 5: Present Findings

Group all findings by type. For `--dry-run`, stop here — report only, no changes.

```markdown
## Link Repair Scan

Scanned: N files | Excluded: 40-archive/, _templates/, system files

### Broken Wikilinks (N found)

| Source File | Broken Link | Proposed Fix | Confidence |
|---|---|---|---|
| path/to/note.md:12 | [[old-name]] | [[correct-name]] | High |
| path/to/other.md:8 | [[typo-link]] | — | No match |

### Orphan Notes (N found)

| Orphan Note | Domain | Proposed MOC |
|---|---|---|
| 30-resources/backend/note.md | work | MOC-API-Design |
| 30-resources/data/note.md | work | MOC-Retrieval |

### Escape-Character Bugs (N found)

| File | Line | Issue | Fix |
|---|---|---|---|
| path/to/note.md:5 | [[name.md]] | Remove .md extension | [[name]] |
```

### Step 6: Interactive Repair

Unless `--dry-run` is set, proceed to fix each category in order:

**Broken links first:**
- For auto-fixable links (single match, high confidence): show the fix, apply with confirmation
- For ambiguous links: show options, ask user to pick
- For no-match links: list them at the end as "needs manual review"
- If user says "fix all" or "yes to all", apply all auto-fixable links without further prompts

**Orphans second:**
- For each orphan, show the proposed MOC addition
- Read the target MOC to find the right section for insertion
- Add `- [[note-name]]` under the appropriate heading in the MOC
- Confirm each addition (or batch with "fix all")

**Escape bugs third:**
- Apply `.md` extension removal and bracket fixes with confirmation
- Skip Dataview query issues (flag only — manual fix recommended)

**For every modified file:** Update the `updated:` frontmatter field to today's date.

### Step 7: Report

Output a final summary:

```markdown
## Link Repair Summary

- Broken links fixed: N
- Orphans linked: N
- Escape bugs fixed: N
- Remaining (needs manual review): N

### Manual Review Needed
- [[missing-target]] referenced from path/to/note.md (target doesn't exist)
```

## Rules

- **Show before changing** — always present findings before applying any fix
- **Never delete notes or links** — only fix broken links or add new links
- **Propose, then confirm** — each fix requires user confirmation unless "fix all" is given
- **Update `updated:` frontmatter** on every modified note
- **Skip `40-archive/`** — archived notes are expected to have stale references
- **Skip system files** — `_templates/`, `_meta/scripts/`, `_meta/mcp-server-py/`, SKILL.md backups, README files
- **Don't touch Dataview blocks** — flag escape issues inside ```dataview fences but don't auto-fix
- **Respect existing link aliases** — when fixing `[[broken|My Alias]]`, preserve the alias: `[[correct|My Alias]]`
- **After all fixes**, suggest: "Rebuild the manifest index (hive_rebuild, or python _meta/scripts/build-manifest.py)."
- **One summary line** for terminal: "Link repair: N fixed, N linked, N flagged for review."
- End with Recommended Next Steps
