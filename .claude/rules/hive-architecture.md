# Hive Architecture Conventions

## Folder Structure

```
hive/
├── 00-inbox/           # Unprocessed captures → triage into the PARA folders (stays FLAT)
├── 10-projects/        # Active PARA projects — ONE SUBDIR PER PROJECT SLUG
│   └── <project-slug>/ # All of a project's notes, ADRs, meeting notes
├── 20-areas/           # Ongoing areas of responsibility — one subdir per area
│   ├── reliability/
│   ├── code-review/
│   └── on-call/
├── 30-resources/       # Reference material — one subdir per domain (tag vocabulary)
│   ├── agent-sdk/
│   ├── mcp-gateway/
│   ├── evals-observability/
│   ├── reliability-guardrails/
│   └── synthesis/      # Cross-domain pattern notes from /connect
├── 40-archive/         # Completed/deprecated (status: archived) — MIRRORS SOURCE PATHS
│   └── <original-path> # e.g. 40-archive/10-projects/<slug>/, 40-archive/30-resources/agent-sdk/x.md
├── 50-maps/            # Maps of Content (MOCs) by domain (stays FLAT)
├── memory/             # Deep memory (glossary, people, context, projects)
│   ├── context/
│   ├── people/         # Contact / stakeholder profiles — keep private
│   ├── projects/       # <project>.md — MUST STAY FLAT (exact-path mapping in the MCP server)
│   └── glossary.md
└── _meta/              # System files — hive health, logs, reviews
    ├── reviews/        # Weekly reviews, connection scans
    ├── reports/        # Scheduled outputs
    ├── automation/     # Scheduled task configs
    └── inbox/          # Daily triage logs (auto-generated)
```

Every folder carries a `_README.md` landing page (`type: readme`, a system
note — never counted as content) stating what belongs there and what
doesn't. Read it before filing into an unfamiliar folder.

## Placement Rules

| Creating… | Destination |
|---|---|
| Project note / ADR / meeting note | `10-projects/<project-slug>/` |
| Area working note | `20-areas/<area>/` |
| Reusable pattern / technique | `30-resources/<domain>/` (domain = tag vocabulary) |
| Cross-domain insight | `30-resources/synthesis/` |
| New MOC | `50-maps/` (flat) |
| Raw capture, destination unclear | `00-inbox/` (flat; leaves at triage) |
| Project memory / handoff | `memory/projects/<project>.md` (flat file, append) |

- **Never encode mutable state in paths.** Status (`active`/`queued`/`done`)
  lives in frontmatter; paths are identity for wikilinks and the embedding
  store, so a note moves at most twice in its life: out of `00-inbox/`, and
  into `40-archive/`. No `active/`, `queued/`, `completed/` directories —
  status views come from Dataview dashboards ([[50-maps/MOC-Projects|MOC-Projects]]).
  Rationale: subdirectories are only ever created for *stable* dimensions
  (a project, an area, a domain) — anything mutable in a path forces
  link-breaking moves and re-embedding every time state changes.
- **Archive by mirroring**: `40-archive/<original-path>` — provenance
  survives and un-archiving is a mechanical reverse move.
- **New subdirectory?** Only when a stable dimension earns it (a new
  project, area, or a domain with ≥3 notes) — create it with a `_README.md`
  landing page in the same change.

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
- For real-time metadata queries during Claude Code sessions, prefer `hive_search` / `hive_recent`

**Decision tree — which tool to use:**

| Need | Tool | Requires Obsidian? |
|------|------|-------------------|
| Filter notes by metadata | hivemind (`hive_search`) | No |
| Live dynamic tables in Obsidian | Dataview code blocks | Yes |
| Claude Code reads query results | Serialized query markers | Obsidian must have run recently |
| Complex aggregations | DataviewJS blocks | Yes |
