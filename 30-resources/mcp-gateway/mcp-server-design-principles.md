---
created: 2026-06-08
updated: 2026-06-12
tags:
  - mcp
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# MCP Server Design Principles

One server per domain, thin wrappers over working code, and a tool count treated as a UX budget. Most MCP design mistakes are violations of one of those three.

## One server per domain

A server is a cohesion boundary. Vault retrieval tools belong together; batch-inventory tools belong together; cramming both into one server gives every client a grab-bag namespace and couples two release cadences. The opposite failure — one server per tool — turns client configuration into a shopping list and multiplies process overhead. The test: if two tools share a backend, a data model, or an auth context, they share a server; otherwise they don't.

## Wrap, don't rewrite

When working code exists, the MCP layer should be embarrassingly thin: parse arguments, call the existing function, shape the result. Rewriting logic *into* the server couples business behavior to a protocol adapter and guarantees drift from the original. The wrapper pattern also keeps the server testable — the logic has its own tests; the server needs only contract tests, per [[mcp-server-testing-strategies]].

```text
existing library  ->  thin MCP wrapper  ->  client
      (logic)          (schema + dispatch)
```

## Tool count is a UX budget

The consumer of your tool list is a model deciding what to call. Twenty-three well-named tools with crisp descriptions work; sixty tools with overlapping scopes degrade selection accuracy for *all* of them, because every additional tool is another candidate to confuse with the right one. Consolidate aggressively: a `status` tool with a mode enum beats four near-identical status variants ([[tool-schema-ergonomics]] covers the enum discipline).

## Design for the backend to change

Parameter shapes should describe intent, not implementation: `get_credential(name)` survives a migration from OS keychain to a cloud secrets manager; `read_keychain_entry(service, account)` does not. Backend-agnostic interfaces are what let a server keep its contract while everything behind it moves — and with the contract stable, transport and deployment become independent decisions ([[mcp-transport-tradeoffs]]).

Auth failures deserve first-class design attention too — a server that masks a 4xx behind a cached fallback is lying to its caller ([[auth-failure-semantics]]).
