---
created: 2026-06-20
updated: 2026-06-30
tags:
  - devops
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Nondeterminism Containment

Temperature zero is not determinism, and hoping for repeatable model output is not a reliability strategy. The workable posture: accept that the generative core is stochastic, then contain the stochasticity behind structural constraints and contracts so that *system behavior* stays predictable even when *text* doesn't.

## Why you can't config your way out

Greedy decoding still varies across model versions, batch effects, and infrastructure changes you don't control. Seeds help in narrow lab settings and evaporate in production serving. Chasing bit-identical outputs spends effort on a property you cannot hold — and don't need. Callers rarely require the same words; they require the same *guarantees*.

## Containment layers, outside-in

- **Schema constraints.** Structured output validated at the boundary turns "some text" into "one of a known set of shapes" — the single highest-leverage containment there is. Variance in phrasing becomes invisible because phrasing never crosses the boundary.
- **Contracted tools.** When the only way the model affects the world is through typed tool calls with enums and bounds, the reachable state space is enumerable regardless of what the model was thinking.
- **Invariant checks.** Assert properties of the outcome, not the transcript: the diff touches only allowed paths, totals balance, the output cites files that exist. Invariants are determinism where it matters.
- **Idempotent effects.** When actions can repeat safely ([[retry-idempotency-for-tool-calls]]), run-to-run variance in *how many attempts* something took stops being observable in the final state.

## Measure the variance you keep

Contained nondeterminism is still nondeterminism; measure it. Run stochastic tasks k times in the eval suite and track the pass@k vs pass^k spread — that gap *is* your variance, quantified. A widening gap at constant single-run quality means behavior is getting flakier, which is a regression even if the average holds.

Variance also decides rollout posture: high-variance behavior needs bigger canary samples to detect regressions, which couples containment directly to deploy speed ([[canary-rollouts-for-agent-changes]]). And where variance can't be contained below the tolerance of an irreversible action, the answer is not more sampling — it's a gate ([[blast-radius-limits-for-tools]]).
