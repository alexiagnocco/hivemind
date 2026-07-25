---
created: 2026-06-20
updated: 2026-07-20
tags:
  - meta
status: active
type: moc
domain: work
seed: demo
---

# MOC — Reliability and Guardrails

Map of content for keeping agent systems safe and steady: containing nondeterminism, staging behavioral changes, stopping and resuming long work, bounding what tools can touch, and responding when something goes wrong anyway.

## Containment

- [[nondeterminism-containment]] — structural constraints, not hope about temperature
- [[blast-radius-limits-for-tools]] — permission tiers sized to worst-case misuse

## Change management

- [[canary-rollouts-for-agent-changes]] — a prompt change is a deploy; stage it like one

## Long-running work

- [[cancellation-semantics-for-agent-jobs]] — cooperative cancellation with declared cleanup
- [[checkpoint-restart-for-long-jobs]] — resume tokens and the effect ledger; replay-safe or it didn't happen

## Pressure and failure

- [[rate-limit-backoff-strategies]] — jittered backoff, shared retry budgets, circuit breakers
- [[graceful-degradation-fallback-chains]] — every fallback visible in the response
- [[incident-response-for-agent-systems]] — kill switches, audit trails, runbooks written in peacetime

## Related

- [[ADR-003-agent-job-checkpointing]] — the checkpoint/restart decision these notes support
- [[demo-corpus-readme]] — what this corpus is and how it was made
