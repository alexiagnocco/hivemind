---
created: 2026-06-29
updated: 2026-07-09
tags:
  - testing
  - devops
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Quality Signal Dashboards

A dashboard's job is to answer one question at a glance: *is it worse than yesterday?* Everything on the board either serves that question or dilutes it. Vanity aggregates — total requests, cumulative tokens, all-time success rate — answer "is it busy," which nobody paged anyone over.

## Leading signals over lagging ones

By the time task-success rate visibly drops, users have been living with the regression for days. The signals that move *first*:

- **Retry density** — retries per task. Rises before success rate falls, because the loop is working harder to reach the same outcomes.
- **Steps per completed task** — same logic; effort inflation precedes failure inflation.
- **Error mix by class** — a shift in the tool-rejection vs environment-error ratio ([[error-taxonomy-for-agent-loops]] vocabulary) localizes a problem before it aggregates into anything.
- **Gate escalation rate** — how often the agent punts to a human. A rising punt rate is the agent telling you something changed.
- **Eval flake count** — oscillating pins are an early symptom of behavioral instability ([[regression-pinning-evals]] quarantines them; the *count* belongs here).
- **Judge-human agreement** — the calibration control chart from [[eval-drift-detection]]; when it steps, every other judged number on the board is suspect, so it earns a permanent slot.

For retrieval-backed systems, coverage and precision trend lines — and their product against the decay threshold — are the compounding-health headline ([[retrieval-quality-metrics]]).

## Design rules

- **Every chart is a delta.** Absolute values need tribal knowledge to read; deviation-from-baseline reads instantly. Pin the baseline visibly.
- **Segment by cohort, not just time.** Model version, prompt version, canary vs stable ([[canary-rollouts-for-agent-changes]] depends on this split being one click).
- **Annotate deploys on the time axis.** A quality chart without change markers is a mystery novel with the last chapter torn out.
- **One page.** If it scrolls, the second screen is where incidents hide. Details live in traces ([[agent-tracing-instrumentation]]); the dashboard is the index, not the archive.

The test of a good board: during an incident, nobody opens anything else first.
