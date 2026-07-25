---
created: 2026-06-08
updated: 2026-07-20
tags:
  - meta
status: active
type: moc
domain: work
seed: demo
---

# MOC — MCP and Gateway Patterns

Map of content for MCP server and gateway engineering: server design, schema ergonomics, transport and deployment choices, failure semantics, and the operational plumbing (env resolution, credentials, testing) that decides whether a server survives contact with real environments.

## Server design

- [[mcp-server-design-principles]] — one server per domain; wrap, don't rewrite; tool count as UX budget
- [[tool-schema-ergonomics]] — descriptions the model actually reads; enums beat free strings
- [[tool-result-size-management]] — paginate, truncate with markers, or indirect through artifacts

## Failure semantics

- [[auth-failure-semantics]] — 4xx surfaces to the caller; only 5xx/timeouts may fall back, visibly
- [[credential-handling-in-mcp-servers]] — env var, then keychain, then declared absence

## Deployment and routing

- [[mcp-transport-tradeoffs]] — stdio vs streamable HTTP; the transport decides more than plumbing
- [[gateway-routing-patterns]] — namespacing, allowlists, and quotas at the price of a hop
- [[mcp-server-registry-design]] — versioning and trust tiers before search
- [[launch-wrapper-env-resolution]] — config files don't expand variables; a wrapper owns env

## Verification

- [[mcp-server-testing-strategies]] — in-memory logic tests, contract tests, the stdio handshake

## Related

- [[gateway-shim-consolidation]] — the consolidation project these patterns came out of
- [[ADR-001-mcp-gateway-shim]] — the decision to route everything through one shim
- [[demo-corpus-readme]] — what this corpus is and how it was made
