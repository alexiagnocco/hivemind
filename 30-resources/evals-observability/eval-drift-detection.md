---
created: 2026-06-27
updated: 2026-07-08
tags:
  - testing
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Eval Drift Detection

Two things drift under a stable eval suite: the judge and the task distribution. Both drift silently, both corrupt trend lines, and both need re-calibration on a *cadence* — because drift discovered "on suspicion" is drift discovered after a quarter of decisions were made on corrupted numbers.

## Judge drift

A model-graded criterion is only as stable as the judge behind it. Judges drift when the judge model is upgraded, when the rubric prompt is edited, and — most insidiously — when neither changes but the *distribution of answers being judged* shifts into a region where the judge behaves differently. Verbosity bias, for example, is dose-dependent: a change that makes agents 30% chattier moves judged scores even at constant quality ([[llm-as-judge-caveats]] catalogs the biases; drift is those biases changing magnitude over time).

Detection is re-anchoring: keep a frozen human-labeled calibration set, re-run the judge against it on a schedule, and chart judge-human agreement per criterion. Agreement is a control chart — a step change means the judge moved, and every score since the last green check is suspect. Cheap insurance: version the judge (model ID + rubric hash) on every recorded score, so "which scores are suspect" is a query, not a debate.

## Task-distribution drift

The suite froze last quarter's problems; production moved. Symptom: eval scores hold steady while user-visible quality sinks — the suite is measuring a world that no longer arrives. Detect it by comparing distributions: task type, input length, tool mix, failure classes seen in production traces ([[agent-tracing-instrumentation]] makes those fields queryable) against the same fields in the suite. A widening gap is the drift; sampled production failures are the patch, harvested into new fixtures on the same cadence.

## The cadence, concretely

```text
weekly:    distribution-gap report (suite vs production traces)
monthly:   judge re-anchoring against the frozen human set
quarterly: refresh calibration labels; retire aged fixtures
```

Wire the checks into the same pipeline as the regression gate ([[regression-pinning-evals]]) so they run without being remembered, and chart both agreement and gap trends where the team looks ([[quality-signal-dashboards]]). Offline suites accumulate this debt fastest — the replay-vs-reality gap is structural, not accidental ([[offline-vs-online-agent-evals]]).
