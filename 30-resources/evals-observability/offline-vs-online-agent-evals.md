---
created: 2026-07-01
updated: 2026-07-10
tags:
  - testing
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Offline vs Online Agent Evals

Replay harnesses lie about distribution; canaries lie about coverage. Neither lie is fixable from inside its own method, which is why mature agent teams run both and treat disagreement between them as a first-class signal rather than an inconvenience.

## What offline replay actually measures

An offline suite replays frozen tasks against frozen fixtures ([[eval-suite-design-for-agents]] for the construction). Its virtues are real: deterministic, cheap to run on every commit, safe for changes too risky to ship, and capable of covering rare-but-critical paths at whatever density you choose — the incident that happens yearly in production can run nightly in replay.

Its lie is distributional. The suite contains the tasks someone thought to freeze, weighted by curation, not by arrival rate. Production's task mix drifts away from it continuously ([[eval-drift-detection]] measures the gap), and novel inputs — the ones most likely to break an agent — are by definition absent. A suite can be green for a month while production quality sags, and both readings are "correct."

## What online canaries actually measure

A canary routes a slice of real traffic to the changed agent and compares quality signals against the stable cohort ([[canary-rollouts-for-agent-changes]] owns the rollout mechanics; the dashboard split in [[quality-signal-dashboards]] is what makes the comparison readable). The distribution is real by construction — that is the entire point.

The lie is coverage. A canary sees whatever traffic arrives during its window: rare paths mostly don't, seasonal behavior doesn't, and the sample size on any *segment* may be too small to detect the regression that matters. A canary also cannot evaluate what is too dangerous to ship even to 5% — which is precisely the change that most needs evaluating.

## Use each where it is honest

```text
offline: merge gates, rare paths, dangerous changes, per-commit cadence
online:  distribution truth, integration reality, the final ship decision
```

The compounding move: harvest online failures into offline fixtures, continuously. Every production trace that embarrassed the agent ([[agent-tracing-instrumentation]] retains exactly these) becomes a replay task, which slowly teaches the offline suite the distribution it was lying about. When offline says pass and the canary says fail, believe the canary — then steal its evidence.
