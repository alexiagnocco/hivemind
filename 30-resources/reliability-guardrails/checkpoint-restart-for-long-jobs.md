---
created: 2026-06-26
updated: 2026-07-06
tags:
  - devops
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Checkpoint and Restart for Long Jobs

Durable state plus resume tokens — and one non-negotiable: side effects must be replay-safe, or checkpointing is theater. A checkpoint that faithfully restores the plan while the world holds effects the plan doesn't know about is *worse* than starting over, because it resumes confidently into an inconsistent reality.

## What a checkpoint must capture

For an agent job, the surprising part is how little of the transcript matters. The durable core:

```text
resume token: {
  task definition + goal predicate
  plan state: completed steps, current step, remaining budget
  effect ledger: every mutation performed, with idempotency keys
  open questions / decisions made
}
```

Not the full context window. Restarts re-derive working context from the durable core plus retrieval — which is cheaper and *more correct* than replaying a stale transcript into a fresh session ([[context-budget-management]]'s externalize-before-you-need-it discipline is exactly this). Checkpoint at step boundaries, the same safe points cancellation uses ([[cancellation-semantics-for-agent-jobs]] — design the two together; cancel is "checkpoint, then stop").

## The effect ledger is the hard part

Resume means re-approaching steps that may have half-happened. The ledger records every mutation with enough identity to answer "did this already occur?" — and the answer mechanism is idempotency: re-issue the mutation with the same key and let the backend deduplicate ([[retry-idempotency-for-tool-calls]]). Where a tool offers no idempotency, the ledger must record effect *completion* transactionally with the checkpoint, or that step is a corruption point on every restart. Replay-safe or it didn't happen.

## Restart is a fresh judgment, not a tape replay

Resuming after an hour (or a week) means the world may have moved: files changed, tickets closed, assumptions expired. A good restart re-validates preconditions for remaining steps instead of trusting the frozen plan — plan state is a *hypothesis* on resume, and stale hypotheses get re-planned. Budget accounting carries over; a job must not launder its step budget through repeated restarts ([[plan-act-observe-loop-design]] owns the budget semantics).

Test it the only honest way: kill the job at every checkpoint boundary in a fixture, restart, and assert the final state matches the never-killed run. Restart paths exercised only by real outages are restart paths that fail during them.
