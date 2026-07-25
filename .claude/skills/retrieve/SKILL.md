---
name: retrieve
description: "Composite-scored hive retrieval with MemRL utility weighting. Use when the user says 'retrieve', 'smart search', or 'scored retrieval'. For general hive lookups, prefer /recall instead."
---

# /retrieve — Smart Retrieval

Retrieve hive notes ranked by composite score: text match, freshness, link connectivity, and MemRL utility. This is the scoring engine behind `/recall`, exposed as a standalone tool.

## Usage

`/retrieve <query>` · `/retrieve --project <slug> <query>` · `/retrieve --domain work <query>` · `/retrieve --include-archived`

## Behavior

1. **Query** — Call `hive_retrieve` with the query, optional project/domain filters, and max_results (default 10, respecting the 40% context rule). Pass `detail: "full"` — this skill displays the per-component score breakdown, which only the full tier carries (the default `standard` tier returns path/title/score/summary/updated/tags/utility/status/domain).
2. **Display** — Show results with their composite scores:
   - Path, title, domain, status
   - **Match score** (`matchScore`): how well text matches the query
   - **Freshness** (`freshnessScore`): how recently the note was modified
   - **Connectivity** (`connectivityScore`): how well-linked the note is in the graph
   - **Utility** (`utility`): MemRL learned helpfulness from past feedback
   - **Composite** (`score`): final weighted score
3. **Interpret** — Flag interesting patterns:
   - High utility notes = frequently helpful in past sessions
   - High match but low utility = matches text but rarely used (possible tagging issue)
   - High utility but low match = tangentially related but historically valuable

## vs /recall

| Feature | /retrieve | /recall |
|---|---|---|
| Scoring | Composite + MemRL | Full workflow |
| Graph walk | No | Yes (hive_related) |
| Context load | No | Yes (hive_context) |
| Feedback | Ranked by past feedback | Records new feedback |

## MCP Tool

Primary: `hive_retrieve`
