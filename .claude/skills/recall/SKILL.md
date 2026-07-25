---
name: recall
description: "Structured hive retrieval with relevance ranking. Use when the user says 'recall', 'what do we know about', 'check the hive', 'prior art', 'have we seen this before', or 'search knowledge'."
---

# /recall — Structured Hive Retrieval

Surface relevant hive knowledge before starting work. The sigma lever.

## Usage

`/recall <query>` · `/recall --project <slug>` · `/recall --domain <domain>` · `/recall --deep <query>` · `/recall --recent`

## Behavior

1. **Search** — Use `hive_retrieve` (Hivemind MCP) for composite-scored retrieval with MemRL utility weighting. Use `hive_related` for link-graph neighbors of top results. If Hivemind unavailable, fall back to Grep/Glob across: memory/projects, 30-resources, 30-resources/synthesis, 10-projects, 20-areas, 50-maps.
2. **Rank** — by z_norm(match×3 + freshness×2 + connectivity×1) + lambda × z_norm(utility). Notes with high past utility rise.
3. **Present** — grouped as Directly Relevant, Related Context, Archived (flagged stale). Max 10 results (40% rule). Include utility score when available.
4. **Report gaps** — "No hive content for X — capture after this session with `/retro`"
5. **Track retrieval** — save the `retrievalId` from results for feedback correlation.

## Output Format

```
## Recall: "<query>" (retrievalId: YYYYMMDDHHMMSS)
### Directly Relevant (N)
- [[note]] — summary (updated: YYYY-MM-DD) [status] (utility: 0.XX)
### Related Context (N)
- [[note]] — relationship
### Gaps
- Topics with no coverage
```

## Feedback Loop (MemRL)

After the session uses (or doesn't use) recalled notes:

1. **Helpful notes** — call `hive_feedback` with paths of notes that were actually referenced or influenced decisions, `helpful=true`, and the `retrievalId`.
2. **Unused notes** — call `hive_feedback` with paths of recalled notes that weren't used, `helpful=false`.
3. **Skip if unclear** — only record feedback when usage is unambiguous.

This feedback trains the utility scores over time. Notes that consistently help rise in future rankings; noise sinks.

## Rules

- Always show `updated:` dates (freshness matters)
- Flag archived notes
- Max 10 results unless `--deep`
- Gaps are as important as hits
- Record feedback when note usage is clear — this is how sigma and rho become real measurements
