---
created: 2026-06-22
updated: 2026-07-02
tags:
  - devops
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Canary Rollouts for Agent Changes

A prompt change is a deploy. It ships like a copy edit — one string, no compile step, invisible in a diff scan — and it changes production behavior as much as a code change, sometimes more. Stage it like one: canary cohort, quality signals as the tripwire, rollback as the default response to ambiguity.

## What counts as a deploy

Everything that can move agent behavior: prompt text, tool schemas and descriptions, model version, retrieval configuration, temperature and sampling settings, context assembly order. Model-version bumps are the sneakiest — "same prompt, newer model" is a different system wearing the same clothes. If a change can alter what the agent does, it goes through the pipeline; the pipeline's front gate is the offline regression suite ([[regression-pinning-evals]]), and the canary is the back gate that catches what replay structurally misses ([[offline-vs-online-agent-evals]]).

## The rollout shape

```text
5% cohort, 24-48h  ->  25%, 24h  ->  100%
tripwire: any leading signal regresses beyond threshold -> auto-rollback
```

Cohort assignment must be sticky (a user bouncing between agent versions mid-task generates garbage signal on both sides) and the comparison must be cohort-vs-cohort over the same window — not canary-vs-last-week, which confounds the change with time.

## Tripwires: leading signals, pre-committed

Decide *before* the rollout which signals abort it: retry density, steps-per-task, error-class mix, gate-escalation rate ([[quality-signal-dashboards]] has the menu and the cohort split). Success rate alone is too slow — effort inflation precedes failure inflation. Pre-commitment is the discipline: thresholds chosen during the incident get negotiated by whoever wants to ship.

Sample-size honesty matters more for agents than services: high-variance behavior needs more traffic to distinguish regression from noise ([[nondeterminism-containment]] quantifies the variance), so small canaries on noisy behavior should run *longer*, not get promoted on vibes.

## Rollback is a capability, not an apology

Keep the previous configuration hot and the switch instant — a rollback that needs a redeploy is a decision with a tax on it, and taxed decisions get deferred. Trace canary traffic at full payload retention ([[agent-tracing-instrumentation]]); when the canary fails, those transcripts are the diagnosis, and harvested into fixtures they are also the regression test that prevents the sequel.
