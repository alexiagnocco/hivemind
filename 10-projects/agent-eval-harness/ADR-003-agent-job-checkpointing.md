---
created: 2026-07-02
updated: 2026-07-02
tags:
  - architecture
  - devops
status: active
type: decision
domain: work
decision: accepted
context: "Long agent jobs losing all progress on interruption; reruns duplicating side effects"
seed: demo
---

# ADR-003 — Checkpoint/Restart with Resume Tokens for Jobs Over Five Minutes

**Status:** accepted, 2026-07-02

## Context

Agent jobs running longer than a few minutes — migrations, sweeps, multi-file refactors — currently restart from zero on any interruption: worker recycle, session limit, cancellation. Two incidents this quarter: a forty-minute sweep interrupted at minute thirty-eight reran from scratch and double-created records because two of its mutations were not safely repeatable.

## Decision

Jobs with an expected runtime over five minutes checkpoint at step boundaries. A checkpoint is a resume token: task definition and goal, plan state with remaining budget, an effect ledger recording every mutation with its idempotency identity, and open decisions. Restart consumes the token, re-validates preconditions for remaining steps, and re-issues ambiguous mutations under their original idempotency keys ([[checkpoint-restart-for-long-jobs]] is the full pattern; the effect ledger is the load-bearing part).

Corollary adopted with the same decision: mutating tools used by long jobs must offer idempotency keys or documented natural idempotency — the replay-safety requirement makes this non-optional, and cancellation shares the same safe points ([[cancellation-semantics-for-agent-jobs]]).

## Alternatives considered

**Rerun-from-scratch, hardened (rejected).** Make all long jobs cheap to rerun instead of resumable. Rejected on cost (a rerun repays the full token spend) and on correctness: "cheap to rerun" still requires the same idempotency work to avoid duplicate effects — the hard part of checkpointing without its benefit.

**Full context-window snapshotting (rejected).** Serialize the entire transcript and restore it verbatim. Rejected: heavy, couples resume to a model version, and restores *stale* working context — re-deriving context from the durable core plus retrieval is cheaper and more correct.

## Consequences

Step boundaries become mandatory structure for long jobs (no monolithic mega-steps). The effect ledger adds a write per mutation — negligible against mutation cost. Restart-path testing enters the fixture suite: kill at every boundary, restart, assert end-state parity with the uninterrupted run. Budget accounting survives restarts, so a job cannot launder its step budget through repeated interruptions.
