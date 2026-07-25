---
description: Vault folder structure, naming conventions, and linking rules
globs: "**/*.md"
---

# Vault Architecture Conventions

## Folder Structure

```
vault/
├── 00-inbox/           # Unprocessed captures → triage into the PARA folders
├── 10-projects/        # Active PARA projects (status: active)
├── 20-areas/           # Ongoing areas of responsibility
│   ├── reliability/
│   ├── code-review/
│   └── on-call/
├── 30-resources/       # Reference material, guides, how-tos
│   ├── agent-sdk/
│   ├── mcp-gateway/
│   ├── evals-observability/
│   ├── reliability-guardrails/
│   └── synthesis/      # Cross-domain pattern notes from /connect
├── 40-archive/         # Completed/deprecated (status: archived)
├── 50-maps/            # Maps of Content (MOCs) by domain
├── memory/             # Deep memory (glossary, people, context, projects)
│   ├── context/
│   ├── people/         # Contact / stakeholder profiles — keep private
│   ├── projects/
│   └── glossary.md
└── _meta/              # System files — vault health, logs, reviews
    ├── reviews/        # Weekly reviews, connection scans
    ├── reports/        # Scheduled outputs
    ├── automation/     # Scheduled task configs
    └── inbox/          # Daily triage logs (auto-generated)
```

## Naming Conventions

- **General note**: `lowercase-kebab-case.md` (e.g., `auth-token-expiry-bug.md`)
- **Meeting note**: `YYYY-MM-DD-meeting-topic.md` (e.g., `2026-03-18-meeting-roadmap-review.md`)
- **Decision record**: `ADR-NNN-title.md` (e.g., `ADR-001-event-sourcing-architecture.md`)
- **MOC**: `MOC-Topic-Name.md` (e.g., `MOC-API-Design.md`)
- All filenames: lowercase (except MOC/ADR prefixes), hyphens for spaces, no special characters

## Linking Rules

- Use `[[wikilinks]]` exclusively — never bare filenames for internal references
- For section references: `[[note-name#heading]]`
- Every note should link to its parent MOC or project
- MOCs should link to all notes in their domain
- Use the `parent:` frontmatter field to establish hierarchy
- When moving/renaming files, update ALL inbound links
- Every note should have at least one inbound link (no orphans)

## Dataview Integration

- Claude can read and write Dataview queries but cannot execute them.
- When creating dashboard notes or MOCs, include appropriate Dataview queries.
- Use DQL (```dataview) for simple filter/sort/table queries.
- Use DataviewJS (```dataviewjs) only for aggregations, loops, or metadataCache access.
- Never modify existing Dataview queries without explicit instruction.

### Serialized Queries (Dataview Serializer Plugin)

The Dataview Serializer plugin writes query results as static markdown between HTML comment markers. This is the bridge that lets Claude Code read Dataview output.

**Reading serialized results:**
- Results live between `<!-- SerializedQuery: ... -->` and `<!-- SerializedQuery END -->` markers
- DataviewJS results use `<!-- SerializedDataviewJS -->` / `<!-- SerializedDataviewJS END -->`
- Read these markers like any other markdown — they contain tables, lists, or raw text

**Writing new queries to MOCs/dashboards:**
- Always add a `<!-- QueryToSerialize: {DQL} -->` comment so results are available to Claude Code
- DQL queries use `QueryToSerialize` (auto-updates on file save in Obsidian)
- DataviewJS queries use `DataviewJSToSerialize` or `DataviewJSToSerializeManual` (manual trigger via Command Palette)
- One-time queries: `QueryToSerializeOnce` (serializes once, then stops updating)

**Staleness caveat:**
- Serialized results are snapshots — they update only when the file is opened or modified in Obsidian
- If a MOC hasn't been opened in Obsidian for 7+ days, serialized results may be stale
- For real-time metadata queries during Claude Code sessions, prefer `vault_search` / `vault_recent`

**Decision tree — which tool to use:**

| Need | Tool | Requires Obsidian? |
|------|------|-------------------|
| Filter notes by metadata | engram (`vault_search`) | No |
| Live dynamic tables in Obsidian | Dataview code blocks | Yes |
| Claude Code reads query results | Serialized query markers | Obsidian must have run recently |
| Complex aggregations | DataviewJS blocks | Yes |
