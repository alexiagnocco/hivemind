---
created: 2026-06-22
updated: 2026-06-28
tags:
  - mcp
  - testing
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# MCP Server Testing Strategies

Three layers, cheapest first: in-memory tests for logic, contract tests for schemas, and a stdio initialize handshake as the smoke test. Each layer catches a failure class the others structurally cannot.

## Layer 1: in-memory, for logic

Tool logic should be callable without any protocol in the way — plain functions, tested with plain tests. If your server follows the thin-wrapper discipline ([[mcp-server-design-principles]]), this layer already exists as the wrapped library's own suite, and the server adds nothing to test here. If logic can *only* be exercised through the protocol, that is the architecture telling you the wrapper isn't thin.

## Layer 2: contract tests, for the interface

The schema is the product; test it as one. Contract tests boot the server in-process, list the tools, and assert on the surface a client would see:

- Tool names, parameter schemas, and required fields match the pinned contract
- Every enum value routes to a distinct behavior (parameterized, one case per value)
- Malformed arguments produce structured errors with the right class — including the auth cases, where the 4xx-surfaces / 5xx-falls-back split of [[auth-failure-semantics]] is an assertable behavior, not a hope
- Result envelopes carry their declared metadata (pagination cursors, truncation markers per [[tool-result-size-management]])

Snapshot the full tool listing and diff it in CI. A contract change then arrives as a reviewable diff instead of a client-side surprise — the same observed-truth principle a registry should enforce at registration time ([[mcp-server-registry-design]]).

## Layer 3: the stdio handshake, for reality

The cheapest end-to-end test that means anything: pipe a JSON-RPC `initialize` request into the real entry point and assert a well-formed response comes back.

```bash
printf '%s\n' "$INIT_REQUEST" | timeout 20 run-the-server | head -1 | jq -e '.result.serverInfo'
```

This one line catches the failures unit tests never see: broken entry points, import errors under the deployed interpreter, a launch wrapper resolving env wrong ([[launch-wrapper-env-resolution]]), missing runtime deps. Run it in CI *and* at session start in any environment that self-provisions — it is the difference between "tests green" and "actually boots."

Real-client integration tests are worth having but expensive to maintain; keep them to a handful of golden paths. And note what none of these layers measure: whether the tools actually help an agent succeed at tasks. That is a behavioral question, answered by graded eval suites rather than contract assertions — [[eval-suite-design-for-agents]] picks up where the handshake stops.
