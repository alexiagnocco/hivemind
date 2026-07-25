---
created: 2026-06-03
updated: 2026-07-08
tags:
  - mcp
  - architecture
status: active
type: project
domain: work
project: gateway-shim
priority: high
seed: demo
---

# Project — Gateway Shim Consolidation

Consolidate seven direct tool integrations behind a single MCP gateway shim, so that policy, namespacing, and quotas live in one place instead of being re-implemented (differently) in every client config.

## Why

Each agent client currently wires its own tool servers directly: seven integrations, seven allowlist copies, no shared quota, and tool-name collisions resolved ad hoc per client. Every policy change is N config edits, and the N configs have already drifted. The shim gives us one routing point with namespacing and per-principal allowlists — the tradeoffs and the threshold argument are laid out in [[gateway-routing-patterns]], and this project is the "past the threshold" case.

## Decision record

The architecture decision is captured in [[ADR-001-mcp-gateway-shim]] (accepted 2026-06-05): route all tool calls through the shim; per-client direct config is rejected as the steady state. Key consequence: the shim must not launder failure classes — a 401 from a backing server surfaces as a 401, per [[auth-failure-semantics]].

## Scope

- Shim service exposing namespaced tools from seven backing servers
- Registry entries with contract hashes for each backing server ([[mcp-server-registry-design]] is the pattern; the shim consumes tiers as routing input)
- Allowlist migration from the seven client configs into shim policy
- Per-principal quotas and usage telemetry at the choke point

Out of scope: rewriting any backing server; the shim wraps what exists.

## Status

Five of seven integrations migrated. Contract-hash checks caught one backing server drifting its schema under a stable version string — exactly the failure the registry design predicted. Rollout notes, decisions, and open questions live in the project memory: [[memory/projects/gateway-shim]].

## Working set

- [[gateway-routing-patterns]] — the pattern this project instantiates
- [[auth-failure-semantics]] — failure-class preservation through the shim
- [[mcp-server-registry-design]] — contract hashes and trust tiers
- [[mcp-transport-tradeoffs]] — why the shim runs streamable HTTP while dev servers stay stdio
