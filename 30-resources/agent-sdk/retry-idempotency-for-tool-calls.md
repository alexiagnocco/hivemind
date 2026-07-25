---
created: 2026-06-10
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

# Retry and Idempotency for Tool Calls

Agent loops retry. Transports drop, models re-issue calls after ambiguous observations, and orchestrators re-run steps on resume. The delivery semantics you actually get are at-least-once — so every mutating tool needs an idempotency story, or the retry that saves one task corrupts another.

## The failure that motivates all of this

A `create_ticket` call times out at the transport layer. The ticket was created; the agent never saw the acknowledgment. The loop, reasonably, retries. Now there are two tickets, and nothing in the transcript looks wrong. Multiply by every mutating tool an agent can reach.

## Idempotency patterns, in order of preference

1. **Idempotency keys.** The caller supplies a key per logical operation; the backend deduplicates on it and replays the original result. This is the gold standard because it makes the retry *safe and observable* — the second call returns the first call's outcome.
2. **Natural idempotency.** Upserts, absolute writes ("set status to closed"), and content-addressed operations can be retried freely. Prefer absolute semantics over relative ones: `set_quantity(5)` retries safely, `increment_quantity(1)` never does.
3. **Check-then-act with a unique constraint.** Weakest option — the check races — but a database uniqueness guarantee underneath converts the race into a catchable, classifiable error.

## Retry policy belongs to the error class

Not everything deserves a retry. A transport timeout: retry with backoff. A validation rejection: don't retry, fix the arguments. A rate limit: back off on the shared budget, with jitter — the mechanics and the circuit-breaker escalation live in [[rate-limit-backoff-strategies]]. Classifying these correctly is the whole point of an [[error-taxonomy-for-agent-loops]]; a loop with one undifferentiated retry policy will hammer permanent failures and give up on transient ones.

## Design rule

Every tool that mutates state declares, in its contract, either an idempotency key parameter or a documented natural-idempotency guarantee — and the schema review rejects mutating tools that declare neither. This belongs in the same contract discipline as naming and versioning ([[tool-calling-contracts]]). Read-only tools are exempt; that exemption is itself a reason to keep reads and writes in separate tools.
