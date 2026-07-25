---
created: 2026-06-02
updated: 2026-06-10
tags:
  - ai
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Tool-Calling Contracts

A tool schema is an API contract with a language model as the client. Treat it with the same discipline you'd give a public REST endpoint: name for intent, version deliberately, deprecate loudly.

## Name for intent, not implementation

The model chooses tools by reading names and descriptions. `query_orders_by_customer` gets called correctly; `run_sql_v2` gets called creatively. If a tool name describes the mechanism instead of the outcome, the model will route through it for anything the mechanism could plausibly do — and you inherit every misuse as a support burden.

Descriptions are load-bearing documentation. State what the tool does, when to use it, when *not* to use it, and what the result shape is. The tokens are cheap compared to a retry loop caused by ambiguity.

## Constrain inputs structurally

Every parameter that can be an enum should be an enum. Every free-string parameter is a place where the model will eventually invent a value. Defaults belong in the schema, not in prose — a documented-but-unenforced default is a contract violation waiting for a distracted client.

```text
bad:  {"status": "string"}
good: {"status": {"enum": ["open", "closed", "all"], "default": "open"}}
```

## Version like you mean it

Models cache behavior in weights and prompts cache behavior in examples, so a silently changed parameter semantic breaks callers you cannot see. Additive changes are safe; anything else is a new tool name with the old one marked deprecated in its description. Delete the old tool only after telemetry shows zero calls across a full release cycle.

## Contracts imply enforcement

A contract without validation is a suggestion. Validate arguments at the boundary and return structured, machine-readable errors — the model reads error messages and adjusts, so a good error is self-healing documentation ([[structured-output-validation]] covers the output side of the same boundary). Mutating tools additionally owe the caller an idempotency story, because the loop will retry them — see [[retry-idempotency-for-tool-calls]].

Tool granularity is part of the contract too: a tool that does three things has three failure modes and one name. Split until each tool has one reason to fail. The loop that consumes these contracts is designed in [[plan-act-observe-loop-design]].
