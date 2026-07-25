---
created: 2026-06-15
updated: 2026-06-25
tags:
  - testing
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Eval Suite Design for Agents

An agent eval suite is three commitments: graded rubrics instead of exact-match, fixed task fixtures instead of live environments, and a pinned baseline you diff against instead of an absolute bar you argue about. Miss any one and the suite measures noise.

## Graded rubrics, because agent output is a distribution

Exact-match scoring works for classifiers; agents produce artifacts — code, plans, documents — where many surface forms are equally correct. Grade against a rubric of observable criteria ("compiles", "handles the empty case", "cites the source file") with per-criterion pass/fail, and report the profile, not just the total. A single scalar hides *which* capability regressed, and the profile is what makes a failure actionable.

For stochastic tasks, run k trials and report pass@k alongside pass^k (all k succeed). The gap between them is a nondeterminism measurement you get for free — and it tells you whether to fix the task or contain the variance.

## Fixed fixtures, because the environment is a variable

Every task runs against a frozen fixture: pinned repo state, canned API responses, deterministic filesystem. A task that hits a live service measures that service's uptime as much as the agent. Fixture discipline is also what makes failures *reproducible* — an eval failure you can't replay is a rumor.

Version fixtures with the suite. When a fixture changes, every historical score against it becomes incomparable; that is a breaking change and deserves the same ceremony.

## A pinned baseline, because deltas are the signal

The question a suite answers on every run is not "is the agent good" but "did it get worse than the pinned known-good." Maintain the baseline as an artifact — scores plus transcripts — and gate changes on the delta ([[regression-pinning-evals]] covers the gating mechanics). Absolute thresholds rot; deltas stay meaningful as the suite grows.

Two boundary notes: who grades matters — model-graded rubrics inherit judge bias and drift, so calibrate per [[llm-as-judge-caveats]] — and where you run matters, since replay fixtures systematically miss distribution shift ([[offline-vs-online-agent-evals]]). The suite is necessary, not sufficient; instrument production too ([[agent-tracing-instrumentation]]).
