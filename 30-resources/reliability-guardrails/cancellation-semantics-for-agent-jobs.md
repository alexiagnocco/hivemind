---
created: 2026-06-24
updated: 2026-06-24
tags:
  - devops
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Cancellation Semantics for Agent Jobs

A killed agent mid-side-effect is an incident, not a cancellation. Real cancellation is cooperative: the job is *asked* to stop, gets a bounded window to reach a safe point, discharges its cleanup obligations, and reports what state it left behind. Anything less is `kill -9` with extra steps.

## Why agents make this harder than services

A cancelled HTTP request abandons work that was mostly read-shaped. A cancelled agent may be halfway through a *sequence* of mutations — three files written of seven, a ticket created but not linked, a message drafted but unsent. The world now holds a partial intention, and nothing in the process table records which half exists. Cancellation design is deciding, in advance, what happens to that half.

## The cooperative protocol

- **Check at step boundaries.** The loop polls for cancellation between plan-act-observe iterations — never mid-tool-call. Step boundaries are the natural safe points; a loop with explicit termination design already has them ([[plan-act-observe-loop-design]] treats exits as first-class).
- **Bounded grace.** Cooperation needs a deadline or it becomes hostage-taking: signal, wait N seconds for the current step to finish, then escalate to hard kill. The grace period is sized to the longest *legitimate* step, not the longest possible one.
- **Cleanup obligations are declared, not improvised.** Each mutating step registers its compensation (delete the temp branch, release the lock, mark the ticket abandoned) *before* performing the action. On cancel, run the stack in reverse. Obligations improvised at cancel time are obligations skipped.
- **Exit with a classified status.** `cancelled_clean`, `cancelled_dirty` plus an inventory of surviving state — a distinct class in the loop's error taxonomy, because the caller's next move differs entirely between the two ([[error-taxonomy-for-agent-loops]]).

## Cancellation is checkpointing's little sibling

A job that can checkpoint can cancel cleanly almost for free: cancel is "checkpoint, then stop" ([[checkpoint-restart-for-long-jobs]]). Design them together — the safe points coincide, and the state inventory a dirty cancel must report is exactly what a checkpoint records. Idempotent side effects make both dramatically simpler, since a resumed or re-run job can re-execute the ambiguous step safely ([[retry-idempotency-for-tool-calls]]).

The test worth automating: cancel the job at every step boundary in a fixture run and assert the world is either fully clean or fully accounted for. Cancellation paths that are never exercised are cancellation paths that don't work.
