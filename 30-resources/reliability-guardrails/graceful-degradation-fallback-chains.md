---
created: 2026-07-02
updated: 2026-07-13
tags:
  - devops
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Graceful Degradation and Fallback Chains

Every fallback must be visible in the response. That single rule separates graceful degradation from its evil twin — silent degradation, which serves wrong answers with a straight face and lets the caller build on them. A fallback the consumer can't see is not resilience; it's a lie with good intentions.

## The chain, and its admission rules

A fallback chain orders alternatives by fidelity: primary model, then a smaller model; live query, then cache; semantic retrieval, then keyword. Two rules govern admission to the chain:

- **Only availability failures trigger fallback.** Timeouts, 5xx, connection loss — the primary didn't answer. A 4xx rejection *is* an answer, and falling back on it converts an actionable auth or validation signal into a plausible wrong result. This classification-before-fallback discipline is load-bearing ([[error-taxonomy-for-agent-loops]] for the classes; the auth-specific case is its own well of grief).
- **Every hop stamps the response.** `degraded: served-from-cache, age 14h` travels *with the data*, not in a log nobody joins. Labels must survive the full path — server, gateway, tool result, agent observation — because a label lost two hops downstream recreates silent degradation with extra steps.

## Degraded answers change downstream behavior

The stamp isn't decoration; consumers should *act* on it. An agent holding a cache-aged answer should lower its confidence, prefer verification steps, and — critically — not gate an irreversible action on degraded data ([[human-in-the-loop-gates]]: reversibility tiers get stricter when inputs are stamped degraded). A dashboard aggregating degraded-response rate gets an early outage signal the uptime checks miss ([[quality-signal-dashboards]]).

## Design the floor, not just the chain

Chains need a defined bottom: what happens when *every* rung fails? The floor is an honest, classified failure — never a shrug that returns empty-and-200. Failing clean at the floor is what lets the loop re-plan or escalate; the circuit breaker pattern feeds this directly, converting a dead backend into a fast classified failure the chain can route around ([[rate-limit-backoff-strategies]]).

Two operational notes: fallback rungs rot when they're never exercised, so chaos-test the chain by faulting the primary in fixtures on a cadence; and rung *fidelity* drifts — a cache that was 5 minutes stale at design time and is 3 days stale today has silently become a different rung. Stamp the fidelity metadata (age, source, coverage), not just the fact of degradation.
