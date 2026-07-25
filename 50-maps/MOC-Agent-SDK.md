---
created: 2026-06-01
updated: 2026-07-20
tags:
  - meta
status: active
type: moc
domain: work
seed: demo
---

# MOC — Agent SDK Patterns

Map of content for agent-loop engineering: loop design, tool contracts, structured boundaries, context economics, and the control surfaces (gates, budgets, error classes) that make an agent shippable rather than just impressive.

## Core loop

- [[plan-act-observe-loop-design]] — termination conditions and step budgets come first
- [[error-taxonomy-for-agent-loops]] — tool vs model vs environment errors; one retry policy each
- [[human-in-the-loop-gates]] — gate on reversibility, not confidence

## Boundaries and contracts

- [[tool-calling-contracts]] — tool schemas as versioned API contracts
- [[structured-output-validation]] — schema-constrained outputs, retry-on-parse-failure
- [[retry-idempotency-for-tool-calls]] — at-least-once delivery demands an idempotency story

## Context and memory

- [[context-budget-management]] — the 40% rule; just-in-time loading; deliberate compaction
- [[agent-memory-architectures]] — working, episodic, semantic tiers; retrieval beats bigger windows
- [[prompt-cache-alignment]] — stable prefixes; cache design is cost design

## Orchestration

- [[subagent-fanout-patterns]] — fan out for independent work; the audit pass is mandatory

## Related

- [[gateway-shim-consolidation]] — project applying the contract discipline at gateway scale
- [[ADR-003-agent-job-checkpointing]] — checkpoint/restart decision for long-running jobs
- [[demo-corpus-readme]] — what this corpus is and how it was made
