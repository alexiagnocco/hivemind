---
created: 2026-06-24
updated: 2026-07-16
tags:
  - testing
  - ai
status: active
type: project
domain: work
seed: demo
---

# agent-eval-harness — Project Memory

Accumulated context for the eval harness buildout. Landing note: [[agent-eval-harness-buildout]].

## Session Handoff — 2026-06-24

### What Was Done
- First fixture set frozen: twelve tasks across the two highest-traffic agent task classes, environments pinned (canned API responses, fixed repo states).
- Rubrics written as binary per-criterion checks. Started from 1-10 quality scales; abandoned them within a day — two graders (one human, one model) disagreed constantly on scales and almost never on binary questions. [[llm-as-judge-caveats]] predicted exactly this; should have started there.
- Baseline captured and pinned per [[regression-pinning-evals]]: score profiles, not raw text, after the first harmless-rewording false alarm.

### Decisions Made
- Judge-graded criteria limited to the four that resist mechanical checking; everything else is asserted structurally. Judge calibrated against a 60-item human-labeled set; per-criterion agreement recorded and re-checked monthly ([[eval-drift-detection]] cadence adopted as written).
- CI gate scoped by path filter (prompts, schemas, retrieval config, model pins) rather than running on every commit — per [[ADR-002-eval-gating-in-ci]], the full-suite-always option stays deferred until runtime drops.

### Open Questions
- Flake policy: two tasks show run-to-run variance in one criterion each. Quarantine now, or tighten the tasks first?

## Session Handoff — 2026-07-16

### What Was Done
- Gate live for one month on both agents. Three real regressions blocked at merge time — all three were "trivial" prompt edits, which is the entire thesis validated.
- Flake question resolved: one task tightened (the variance was a genuinely ambiguous fixture), one criterion quarantined with its count charted on the quality board ([[quality-signal-dashboards]]). Widening tolerance was proposed and rejected — a tolerant pin protects nothing.
- Added pass@k reporting for the three stochastic task classes; the pass@k vs pass^k gap is now a tracked variance metric ([[nondeterminism-containment]] uses this same spread as its containment measure).

### Decisions Made
- Production failure harvesting begins: sampled failed traces become candidate fixtures on a weekly cadence, closing the distribution gap the offline suite accumulates ([[offline-vs-online-agent-evals]] — the harvest loop is the mitigation we committed to).

### Open Questions
- Suite runtime is creeping toward the pain threshold that re-opens the deferred full-suite-always decision. Watch it.

### Next Session Start
- Wire the weekly harvest job; review the first batch of harvested fixtures before they enter the suite.
