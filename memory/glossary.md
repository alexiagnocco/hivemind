---
created: 2026-06-01
updated: 2026-07-20
tags:
  - meta
status: active
type: reference
domain: work
seed: demo
---

# Glossary

Working vocabulary for the demo corpus. Each term links to the note that treats it in depth.

- **Agent loop** — the plan-act-observe cycle plus its termination design: goal predicate, step budget, stuck detection. See [[plan-act-observe-loop-design]].
- **Tool-calling contract** — a tool schema treated as a versioned API contract: intent-revealing name, constrained parameters, deliberate deprecation. See [[tool-calling-contracts]].
- **Idempotency key** — caller-supplied identity for a mutating operation so retries deduplicate instead of duplicating. See [[retry-idempotency-for-tool-calls]].
- **Context budget** — the discipline of keeping the working window ~40% full, loading just-in-time, and compacting deliberately. See [[context-budget-management]].
- **MCP gateway** — a single routing point in front of multiple MCP servers providing namespacing, allowlists, and quotas. See [[gateway-routing-patterns]].
- **Canary rollout** — staging a behavioral change (prompt, model, config) on a traffic slice with pre-committed quality tripwires. See [[canary-rollouts-for-agent-changes]].
- **LLM-as-judge** — using a model to grade outputs; usable only with bias controls and human-anchored calibration. See [[llm-as-judge-caveats]].
- **Regression pinning** — freezing known-good outputs or score profiles as reviewable artifacts and gating changes on deltas. See [[regression-pinning-evals]].
- **Retrieval coverage (sigma)** — of the knowledge that would have helped, the fraction retrieval actually surfaced. See [[retrieval-quality-metrics]].
- **Retrieval precision (rho)** — of what retrieval surfaced, the fraction that proved useful. See [[retrieval-quality-metrics]].
- **Escape velocity** — the compounding condition: coverage times precision outrunning knowledge decay (sigma x rho > delta/100). See [[retrieval-quality-metrics]].
- **Blast radius** — the worst-case reach of a tool's misuse; the property permission tiers are sized against. See [[blast-radius-limits-for-tools]].
