---
created: 2026-06-12
updated: 2026-06-24
tags:
  - mcp
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# MCP Transport Tradeoffs

stdio and streamable HTTP are not interchangeable plumbing — they impose different lifecycles, concurrency models, and deployment shapes, and the transport choice quietly decides several architecture questions you thought were still open.

## stdio: the local default

The client spawns the server as a child process and speaks JSON-RPC over pipes. Its virtues are operational: no ports, no TLS, no auth handshake — process identity *is* the auth boundary. Its costs follow from the same fact:

- **Lifecycle is coupled.** One client, one server instance, dying together. State that must outlive the client needs to be externalized anyway.
- **Environment is inherited, not configured.** The server sees whatever env the spawning client passes — which is exactly why launch wrappers exist ([[launch-wrapper-env-resolution]]); config-file env blocks are not a reliable channel.
- **Concurrency is per-process.** Parallel clients mean parallel spawns; a shared cache or index needs file-level coordination, not in-memory assumptions.

The initialize handshake over stdio doubles as the cheapest smoke test a server can have ([[mcp-server-testing-strategies]]).

## Streamable HTTP: the shared-service shape

One long-lived server, many clients, real auth. Choose it when the server holds expensive shared state — a large index, a warm model, a connection pool — or when consumers are remote by nature. The bill:

- **You now run a service.** Deployment, TLS, tokens, versioned upgrades, and an availability story; the 4xx/5xx discipline of [[auth-failure-semantics]] stops being theoretical.
- **Sessions need managing.** Reconnects and resumption are your problem, not the process table's.

## The decision, compressed

```text
local dev tools, per-user state, secrets from OS keychain  -> stdio
shared index, remote consumers, multi-tenant, heavy warmup -> streamable HTTP
```

Design the server so the transport is a boundary, not a load-bearing wall: keep tool logic transport-agnostic and let the adapter own the wire. Servers that do this migrate from local stdio to a hosted gateway without touching a tool signature — which, at gateway scale, is the migration you should assume is coming ([[gateway-routing-patterns]], [[mcp-server-design-principles]]).
