---
name: new-note
description: Create a new note with proper frontmatter, naming, and linking. Use when starting a new note to ensure it follows hive conventions from the start.
allowed-tools: Read, Write, Glob, Grep
---

# New Note

Create a new note following hive conventions. Accepts a topic and optional type as arguments.

## Domain

Always set the `domain` frontmatter field — `work` for engineering content,
`meta` for system files.

**Usage**: `/new-note $ARGUMENTS`
- Example: `/new-note hash-join performance tuning`
- Example: `/new-note meeting with platform team about the rollout plan`
- Example: `/new-note decision: use GitHub Actions over Jenkins`

## Step 1: Determine Note Type

Infer from the arguments or ask:

| Signal | Type | Destination |
|--------|------|-------------|
| "meeting" keyword or attendee names | meeting | `10-projects/<project-slug>/` or `20-areas/<area>/` |
| "decision" or "ADR" keyword | decision | `10-projects/<project-slug>/` |
| Technical topic | note | `30-resources/<domain>/` (domain = tag vocabulary) |
| Cross-domain insight | note | `30-resources/synthesis/` |
| Project-specific content | note | `10-projects/<project-slug>/` |
| Ongoing area of responsibility | note | `20-areas/<area>/` |

## Step 2: Generate Filename

Apply naming conventions from CLAUDE.md:

- Meeting: `YYYY-MM-DD-meeting-topic.md`
- Decision: `ADR-NNN-title.md` (auto-increment NNN)
- General: `lowercase-kebab-case.md`

## Step 3: Create with Frontmatter

Generate the full frontmatter per CLAUDE.md schema. Pre-populate:

- `created:` and `updated:` to today
- `tags:` with 3-5 inferred tags
- `status: draft`
- `type:` per classification above
- Additional fields per note type (project, attendees, etc.)

## Step 4: Scaffold Content

Add minimal structure based on type:

- **Meeting**: `## Attendees`, `## Discussion`, `## Action Items`, `## Related`
- **Decision**: `## Context`, `## Options Considered`, `## Decision`, `## Consequences`, `## Related`
- **Technical note**: `## Summary`, `## Details`, `## Related`
- **General**: `## Notes`, `## Related`

## Step 5: Link

- Add the new note to any relevant MOC in `50-maps/`
- If a closely related note exists, add a `[[wiki-link]]` in both directions

## Step 6: Update Manifest

Run `python _meta/scripts/build-manifest.py` to update the hive index with the new note.

## Output

Create the file and display its path. Open for immediate editing.
