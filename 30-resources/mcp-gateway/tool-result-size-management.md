---
created: 2026-06-20
updated: 2026-06-27
tags:
  - mcp
  - optimization
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# Tool Result Size Management

An unbounded tool result is a context attack you launch on yourself. The consumer of your result is a model with a finite window; a tool that can return 80,000 tokens will eventually do so at the worst moment, evicting the plan, the history, and the reason the call was made.

## Three strategies, in escalation order

**Paginate.** The default for anything list-shaped. Return a bounded page plus an opaque cursor; let the caller decide whether page two is worth the context. Page size is a contract value — declare it in the schema, don't let it drift with the data.

**Truncate with markers.** For single large payloads (logs, file contents, query dumps), return the head, an explicit truncation marker, and the total size. The marker matters more than the truncation: a silently clipped result reads as complete, and the model will reason confidently from the missing half. State what was cut.

```text
[truncated: showing 200 of 14,312 lines; total 1.8 MB]
```

**Indirect through artifacts.** Past a threshold, stop returning content at all. Write the payload somewhere addressable, return a reference plus a summary, and provide a ranged-read tool so the caller can fetch slices on demand. This converts an unbounded response into two bounded ones — and it is the only strategy that scales to results larger than any window.

## Summaries are part of the tool's job

The server knows the payload's structure; the model doesn't. A result envelope that carries shape metadata — row count, field list, min/max timestamps — lets the caller decide its next move without paging through anything. Most "I need the whole result" calls are actually "I need to know what the result contains," and metadata answers that for two hundred tokens. The caller's side of this discipline is summarize-at-the-boundary context hygiene ([[context-budget-management]]).

## Declare the size story in the schema

Size behavior is interface, not implementation: max page size, truncation threshold, and the artifact-indirection cutoff belong in the tool description where the model can read them ([[tool-schema-ergonomics]]). And bound it end to end — a gateway that faithfully relays one server's 200 MB result has failed at its one job of protecting the shared channel ([[gateway-routing-patterns]]).
