---
name: connect
description: Find cross-domain connections and synthesis opportunities between notes. Use to discover hidden relationships between different technical domains.
allowed-tools: Read, Write, Glob, Grep, Bash(find *), Bash(grep *)
---

# Cross-Domain Connector

> **Recommended mode: Plan.** Finding non-obvious connections requires deep reasoning across the full hive. Fast mode will find surface-level matches; plan mode finds the insights that make this skill worthwhile. Switch with `Shift+Tab` if needed.

Surface non-obvious connections between notes across different domains. This is where the second brain earns its name.

## Step 1: Build a Concept Index

Use `hive_manifest()` to get the full hive index. For notes that look promising for connections, use `hive_read()` to get full content. This replaces manual file scanning.

For each note outside `00-inbox/` and `40-archive/`, extract:

- Primary topic/concept
- Domain (backend, data, infra, testing, project, etc.)
- Key terms and themes

## Step 2: Find Cross-Domain Bridges

Look for connections that span domain boundaries:

- **Pattern transfer**: A technical approach in one domain that maps to another (e.g., database query-plan caching ↔ embedding-vector caching)
- **Shared concepts**: Notes in different domains discussing the same underlying idea (e.g., "backpressure" appearing in both a streaming-pipeline note and an API rate-limiting note)
- **Complementary knowledge**: A resource in one domain that would strengthen work in another
- **Temporal clusters**: Notes from the same time period across different domains that may share context

## Step 3: Find Intra-Domain Gaps

Within a single domain, look for:

- Notes that discuss related topics but don't link to each other
- Chains of reasoning that are spread across multiple notes but not threaded together
- Contradictions or evolved thinking (an older note says X, a newer note implies not-X)

## Step 4: Propose Synthesis Notes

For the most valuable connections found, propose new notes that would:

- Bridge two domains with a synthesis insight
- Thread together a chain of related notes into a coherent narrative
- Capture an evolved position that supersedes older notes

Format each proposal:

```markdown
### Connection: [Title]

**Bridges**: [[note-a]] ↔ [[note-b]] (↔ [[note-c]]...)
**Insight**: [1-2 sentence description of the connection]
**Proposed action**: [New note | Add link | Update MOC | Merge notes]
```

## Step 5: Update MOCs (--update-moc)

When invoked with `--update-moc`, or when Step 3 finds 3+ notes missing MOC links:

1. For each unlinked note, identify the best-fit MOC from `50-maps/MOC-*.md` based on domain, tags, and topic overlap
2. Read the target MOC and find the appropriate section/table to insert the note
3. Add a `[[wikilink]]` entry to the MOC in the correct position (alphabetical or by date, matching existing format)
4. Add a `parent: "[[MOC-Name]]"` to the note's frontmatter if missing
5. Update `updated:` on both the note and the MOC

If no suitable MOC exists, propose creating one (but only if 5+ notes would belong to it).

## Step 6: Update Open Questions

Append any interesting unresolved threads to `_meta/open-questions.md`.

## Output

Display top 5 connections in the terminal, ranked by novelty and value. If proposing new synthesis notes, draft them but save to `00-inbox/` for user review before filing.

## Philosophy

The goal is serendipity through structure. The best connections are surprising but, once seen, feel obvious. Don't force connections that aren't there — quality over quantity.
