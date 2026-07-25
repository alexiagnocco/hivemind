---
created: 2026-06-23
updated: 2026-07-05
tags:
  - retrieval
  - testing
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Retrieval Quality Metrics

Coverage and precision are different failures with different fixes, and a retrieval system scored on one number will quietly optimize the wrong one. Measure both, separately, and treat their product as the health signal.

## The two axes

**Coverage (sigma)** — of the knowledge that *would have helped*, how much did retrieval actually surface? Low coverage looks like an agent re-deriving things the knowledge base already contains. It is invisible in the retrieval logs — the damning evidence is in the *work*, where a known answer got rebuilt from scratch. Coverage failures are indexing failures, connectivity failures (the note existed but nothing linked to it), or query-formulation failures.

**Precision (rho)** — of what retrieval surfaced, how much was actually useful? Low precision looks like context stuffed with plausible-but-idle documents, each one taxing the window ([[context-budget-management]] pays that tax downstream). Precision failures are ranking failures.

The compounding condition worth pinning on a dashboard: retrieval only pays for itself when the product sigma x rho outruns the decay rate of the knowledge base — surface enough, surface it accurately, faster than it goes stale.

## Measuring without ground truth

Classic IR metrics (recall@k, MRR, nDCG) assume labeled relevance. Working systems approximate with usage signals:

- **Citation rate** — retrieved items later cited in the output. The numerator of a practical rho: `utility = citations / retrievals` per item, aggregated per query class. Cheap, automatic, and honest — an item retrieved fifty times and cited never is measured noise.
- **Re-derivation audits** — sample completed tasks, check whether existing knowledge was rebuilt. The only honest sigma estimate, and it requires reading transcripts, so sample.
- **Ranking sanity checks** — a small pinned set of query-to-expected-note pairs, run as a regression suite ([[regression-pinning-evals]]); MRR over that set catches ranking regressions before users do.

## The signals are also training data

Citation-based utility isn't just a metric — fed back into ranking as a learned re-ranking term, it closes the loop and makes the retriever sharpen with use ([[feedback-loops-for-ranking]]). Chart sigma, rho, and their product over time ([[quality-signal-dashboards]]); a falling product with stable components means the knowledge base is decaying faster than retrieval improves — a content problem no ranking fix will touch.
