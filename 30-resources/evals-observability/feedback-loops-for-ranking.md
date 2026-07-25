---
created: 2026-06-25
updated: 2026-07-07
tags:
  - retrieval
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Feedback Loops for Ranking

A ranker that never learns which results got *used* is frozen at its priors. The cheapest loop that actually works: harvest implicit citation signals, maintain a per-item utility score as an exponential moving average, and blend that score into the ranking function. Retrieval feeds work, work emits signal, signal sharpens retrieval.

## Implicit beats explicit, almost always

Explicit feedback ("was this helpful? y/n") has response rates too low and biases too strong to rank on. Implicit signals are abundant and honest:

- **Citation** — the retrieved item was referenced in the produced artifact. The strongest signal; it means the item changed the output.
- **Dwell/expansion** — the item was opened and read beyond its summary. Weaker, but cheap.
- **Silent pass** — surfaced, never touched. The negative signal, and the one naive systems forget to record: an item that is *always* surfaced and *never* used is actively costing precision ([[retrieval-quality-metrics]] counts that cost as rho).

Log all three per retrieval event, keyed by item and query class. In agent systems the "user" is often the agent itself, which makes citation detection mechanical: diff the output against the retrieved set.

## EMA utility: simple, stable, forgiving

Per item, keep one number:

```text
utility_new = alpha * reward + (1 - alpha) * utility_old    (alpha ~ 0.3)
```

Reward is 1 on citation, a small positive on expansion, 0 on silent pass. The EMA forgets slowly enough to survive noisy weeks and fast enough to demote an item the corpus has outgrown. Blend it into the final ranking as a weighted term alongside relevance — never as a filter, because a utility of zero must still be escapable (see cold start).

## The two failure modes to engineer against

**Cold start.** New items have no utility history and would rank behind incumbents forever. Give them a neutral prior, not zero, and let relevance carry them until signal accumulates.

**Feedback collapse.** High-utility items get surfaced more, so they get cited more, so they rank higher — a rich-get-richer loop that entrenches yesterday's answers. Cap the utility term's weight, and audit periodically for strong items that never surface. This is one memory tier training another, and the same dynamics govern agent memory generally ([[agent-memory-architectures]]).

Judge-labeled relevance can substitute where citation volume is thin — with every caveat in [[llm-as-judge-caveats]] applied.
