---
created: 2026-06-15
updated: 2026-07-20
tags:
  - meta
status: active
type: moc
domain: work
seed: demo
---

# MOC — Evaluation and Observability

Map of content for measuring agent systems: eval suite construction, judge calibration, regression gating, tracing, retrieval quality, and cost attribution. The organizing idea: deltas against pinned baselines beat absolute scores, and leading signals beat lagging ones.

## Eval construction

- [[eval-suite-design-for-agents]] — graded rubrics, fixed fixtures, pinned baselines
- [[regression-pinning-evals]] — pins as reviewable artifacts; gate merges on deltas
- [[llm-as-judge-caveats]] — the bias inventory; calibrate against humans or don't trust deltas
- [[eval-drift-detection]] — the judge and the task distribution both drift; re-calibrate on a cadence
- [[offline-vs-online-agent-evals]] — replay lies about distribution, canaries lie about coverage

## Observability

- [[agent-tracing-instrumentation]] — one span per tool call; payloads by reference; sample by policy
- [[quality-signal-dashboards]] — "is it worse than yesterday," answered at a glance
- [[token-cost-observability]] — attribution at the span; ratios catch what totals hide

## Retrieval measurement

- [[retrieval-quality-metrics]] — coverage and precision are different failures
- [[feedback-loops-for-ranking]] — citation signals and EMA utility; the ranker that learns

## Related

- [[agent-eval-harness-buildout]] — project that stood this tooling up in CI
- [[ADR-002-eval-gating-in-ci]] — the decision to block merges on eval regressions
- [[demo-corpus-readme]] — what this corpus is and how it was made
