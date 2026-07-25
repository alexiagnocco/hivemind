---
created: 2026-07-03
updated: 2026-07-10
tags:
  - testing
  - optimization
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Token Cost Observability

Unattributed spend makes optimization guesswork. "The bill doubled" is not actionable; "the summarizer agent's cache-hit rate collapsed after Tuesday's refactor" is a one-line fix. The difference is attribution, and attribution is a tagging discipline, not a finance report.

## Attribute at the span, aggregate everywhere

Every model request should carry its cost identity at emission time: agent, feature, task class, model, prompt version, cohort. If tracing is in place, these are span fields and cost queries are group-bys ([[agent-tracing-instrumentation]] is the substrate — cost observability is one of its dividends, not a separate system). Retrofitting attribution from invoices is archaeology; tagging at emission is free.

The fields that earn their place:

```text
agent / feature     -> who to talk to about it
task class          -> unit economics (cost per resolved task, not per request)
model + prompt ver  -> which change moved the number
cached vs fresh in  -> cache health, the silent budget leak
output vs input     -> where the fat actually is
```

## The ratios that catch regressions

Absolute spend tracks usage; *ratios* track efficiency, and efficiency is what regresses silently:

- **Cache-hit fraction of input tokens.** A formatting refactor that breaks prefix stability shows up here first — invisible in review, unmissable on this chart ([[prompt-cache-alignment]] explains the mechanism).
- **Tokens per completed task.** The unit-economics headline. Rising tokens-per-task with flat success rate means effort inflation — the same leading-indicator logic as retry density on the quality board ([[quality-signal-dashboards]]).
- **Input:output ratio per agent.** Sudden input growth usually means context stuffing crept in; sudden output growth means verbosity did.

## Budgets as engineering controls

Per-task-class token budgets, enforced at the loop level, convert cost from a monthly surprise into a per-request decision. Budget exhaustion is then a classified, alertable event — and the alert fires *during* the runaway task, not thirty days later. Set budgets from observed distributions (p95 plus headroom), review them when the distribution moves, and treat a step change in any class's p95 as a regression to bisect like any other ([[regression-pinning-evals]] gates behavior; this gates the cost of behavior).

The spend-shape data also answers design questions: whether an expensive retrieval pass pays for itself is unanswerable without cost-per-task by cohort.
