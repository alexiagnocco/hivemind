---
created: 2026-06-16
updated: 2026-06-28
tags:
  - mcp
  - devops
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# MCP Server Registry Design

A registry's first jobs are versioning and trust, not search. Teams build the catalog UI first because it demos well, then discover that the hard questions — *which version of this server am I actually running, and should I be running it at all?* — have no answers in the data model.

## Versioning before discovery

A registry entry that names a server without pinning its contract version is a pointer to a moving target. The entry needs, minimally:

- **Server version** — the release of the implementation.
- **Contract hash** — a digest over the tool list and schemas, so a client (or gateway) can detect that "same version number" no longer means "same tools." Schema drift under a stable version string is the registry equivalent of a force-push.
- **Compatibility declaration** — which protocol revisions the server speaks.

With a contract hash, upgrades become diffable: the registry can show exactly which tools changed between entries, which is the input a consumer needs before accepting the bump — and the input a canary decision wants.

## Trust tiers, explicitly

Not every registered server deserves the same blast radius. A workable tier model:

```text
tier 0: first-party, reviewed, auto-approved for all clients
tier 1: internal, reviewed, allowlisted per team
tier 2: third-party, sandboxed, read-only tools exposed by default
```

The tier is a *routing input*, not a label: gateways and clients consume it to decide exposure ([[gateway-routing-patterns]]), and a tier change is a reviewable event with an owner. Registries without tiers converge on the worst equilibrium — everything trusted, because untrusting anything breaks someone.

## Registration should verify, not transcribe

An entry created by hand describes what the author *believes* the server does. Registration should instead boot the server and interrogate it — initialize handshake, tool list, schema capture — so the registry records observed truth. The same interrogation is a contract test, which means registration doubles as the server's cheapest CI gate ([[mcp-server-testing-strategies]]).

Keep the registry itself boring: append-only entries, immutable published versions, explicit deprecation with a sunset date ([[mcp-server-design-principles]]'s versioning discipline, applied one level up).
