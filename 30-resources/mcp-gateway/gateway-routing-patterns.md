---
created: 2026-06-14
updated: 2026-06-26
tags:
  - mcp
  - backend
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# Gateway Routing Patterns

A central MCP gateway buys governance at the price of a hop. Whether that trade is good depends on how many clients, servers, and policies you are juggling — below a threshold the gateway is ceremony, above it the per-client config mesh becomes unmanageable and the gateway is the only sane answer.

## What the gateway actually buys

- **Namespacing.** Tool names collide across servers; a gateway prefixes or maps them so `search` from two servers can coexist. Without one, every client resolves collisions locally and differently.
- **Allowlists and policy.** One place to say which principals reach which tools — instead of N client configs each maintaining its own partial copy of the policy, drifting independently.
- **Quotas and telemetry.** Per-tool, per-principal rate limits and a single choke point for usage accounting. Retrofitting either onto a mesh of direct connections is a rewrite disguised as a feature request.
- **Version indirection.** The gateway can route `tools.search` to server v2 for canary traffic while everyone else stays on v1 — deployment flexibility no per-client config can express cleanly.

## What it costs

A hop of latency, a new single point of failure, and — the underrated one — a second schema authority. The gateway re-exposes tool schemas; if it rewrites them (prefixing, description trimming), the schema a model sees is no longer the schema the server published, and debugging a misrouted call now spans two contracts. Keep gateway transformations mechanical and lossless, and let the server registry be the single source of schema truth ([[mcp-server-registry-design]]).

## The failure mode to design against

The gateway inherits every downstream failure and must not launder them: a 401 from a backing server must surface as a 401 to the caller, not become a generic gateway 502 — the classification discipline of [[auth-failure-semantics]] applies with extra force in the middle of the chain, because the gateway is where labels get lost.

## When to skip it

One client and a handful of local stdio servers do not need a gateway; the client's own config *is* the routing table, and the process boundary is the policy ([[mcp-transport-tradeoffs]]). Adopt the gateway when policy, quota, or namespace management stops fitting in one reviewer's head — and consolidate integrations behind it in one deliberate project rather than by attrition.
