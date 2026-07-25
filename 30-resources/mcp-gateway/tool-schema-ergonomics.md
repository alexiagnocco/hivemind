---
created: 2026-06-09
updated: 2026-06-21
tags:
  - mcp
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# Tool Schema Ergonomics

The model reads your schema the way a developer reads API docs — except it reads them on every single call, under token pressure, with no memory of the last call's mistakes. Schema ergonomics are therefore not polish; they are the primary interface.

## Descriptions are documentation the model actually reads

Every tool description should answer four questions in order: what it does, when to use it, when *not* to use it, and what comes back. The "when not" clause is the one everyone omits and the one that prevents the most misrouting — two tools with adjacent purposes need their boundary drawn in prose, in both descriptions.

Parameter descriptions carry the same weight. `path: the path` is a wasted slot; `path: hive-relative path to the note, e.g. 30-resources/backend/retry-patterns.md` eliminates a whole class of malformed calls. Examples in descriptions are cheap and models imitate them.

## Enums beat free strings

Every free-string parameter is a place the model will eventually invent a value. If the legal values are enumerable, enumerate them — the schema then *prevents* the invalid call instead of bouncing it after a round trip. The same goes for formats: pattern-constrain IDs and dates, bound numerics with min/max.

Defaults belong in the schema, declared and visible. A default that lives only in server code is a behavior the model cannot know about and will fight by re-specifying.

## Fewer parameters, flatter shapes

Each parameter is a decision imposed on the caller. Merge parameters that always travel together, drop ones only the server can compute, and keep nesting shallow — deeply nested argument objects fail validation more often for purely structural reasons. When a tool genuinely needs many knobs, that is usually two tools wearing one name ([[mcp-server-design-principles]] treats tool count as a budget, and splitting is often the cheaper spend).

## Errors are schema too

A rejection is part of the interface. Return structured, machine-readable errors with a class field and a corrective hint — the model self-corrects off good errors, and the classification discipline pays into the caller's own handling ([[auth-failure-semantics]] for the auth-specific rules). Results that can be large need a size story declared up front ([[tool-result-size-management]]); "sometimes returns 80,000 tokens" is an ergonomics bug, not a data fact.
