---
created: 2026-06-14
updated: 2026-06-14
tags:
  - ai
  - optimization
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Prompt Cache Alignment

Prompt caching bills you for what changed, not what you sent — but only if the unchanged part is byte-identical and positioned as a stable prefix. Cache design is therefore cost design, and it is decided by how you structure context, not by a flag you flip.

## The mechanics that matter

Caches key on exact prefixes. One byte of drift at position N invalidates everything after N. The practical consequences:

- **Stable content goes first.** System instructions, tool schemas, reference documents — anything that survives across turns belongs at the front, in a fixed order, with fixed formatting.
- **Append, don't edit.** An agent loop that rewrites earlier turns — re-summarizing history in place, reordering tool results — pays full price every step. Append-only context keeps the growing prefix cacheable.
- **Volatile data goes last.** Timestamps, request IDs, and per-turn state at the front of a prompt are a cache-buster you installed yourself. A timestamp in the system prompt is the classic self-inflicted wound: one line invalidates the entire cached prefix every second.

## Where agent loops leak money

Tool results are the big one. A loop that injects large, slightly-different observations early in the context re-buys its own system prompt every iteration. Summarizing observations at the boundary and keeping them in arrival order preserves the prefix — the same move that protects the context budget ([[context-budget-management]]) protects the cache.

Compaction is the other: a compaction pass rewrites history by design, so it invalidates the cache once. That is fine — pay it deliberately, on a boundary you chose, rather than continuously through in-place edits.

## Verify, don't assume

Cache behavior is observable: token accounting per request shows cached versus fresh input. Wire that into your cost telemetry and alert on cache-hit collapse, because a formatting refactor that breaks byte-stability is invisible in review and very visible on the invoice — the attribution mechanics are in [[token-cost-observability]]... which is exactly the kind of number worth watching per agent, per [[plan-act-observe-loop-design]]'s advice to let transcripts, not intuition, drive tuning.
