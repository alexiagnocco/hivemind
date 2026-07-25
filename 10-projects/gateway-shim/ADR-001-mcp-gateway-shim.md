---
created: 2026-06-05
updated: 2026-06-05
tags:
  - architecture
  - mcp
status: active
type: decision
domain: work
decision: accepted
context: "Seven direct tool integrations with drifting per-client allowlists and no shared quota"
seed: demo
---

# ADR-001 — Route All Tool Calls Through an MCP Gateway Shim

**Status:** accepted, 2026-06-05

## Context

Seven tool servers are wired directly into each agent client. Policy (allowlists, quotas) is duplicated per client config and has measurably drifted: an audit found three configs exposing a mutating tool that policy had restricted months ago. Tool-name collisions between two servers are resolved differently in different clients. Every policy change costs N edits and a prayer.

## Decision

Introduce a gateway shim as the single routing point for all tool calls. Clients connect to the shim; the shim namespaces, applies per-principal allowlists and quotas, and routes to backing servers. Direct client-to-server wiring is deprecated as a steady state (grandfathered only for local stdio dev loops).

Constraints the shim must honor:

- **Failure classes pass through untranslated.** A 401/403 from a backing server surfaces as a 401/403 to the caller — the shim must not launder auth rejections into generic gateway errors ([[auth-failure-semantics]]).
- **Schema transformations are mechanical and lossless.** Namespacing may prefix names; it may not rewrite descriptions or parameter schemas.
- **The shim consumes registry trust tiers as routing input** rather than maintaining its own trust judgments.

## Alternatives considered

**Per-client direct config, tightened (rejected).** Keeps the mesh; adds lint tooling to detect drift. Rejected because detection is not prevention — the audit that motivated this ADR *was* the detection tooling working as intended, and the drift happened anyway. N independently-maintained policy copies is the disease, not a symptom.

**Library-level enforcement in a shared client SDK (rejected).** Moves policy into code all clients import. Rejected: policy changes become releases, third-party clients can't be assumed to upgrade, and enforcement in the client is enforcement the client can skip.

## Consequences

One hop of added latency (measured negligible against model latency). The shim becomes a single point of failure and therefore runs with the availability posture of a production service ([[gateway-routing-patterns]] catalogs the full cost side). Policy changes become one edit, reviewable in one place. Implementation is tracked in [[gateway-shim-consolidation]].
