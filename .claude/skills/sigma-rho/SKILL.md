---
description: "Compute true sigma and rho from MemRL feedback data"
---

# /sigma-rho — Retrieval Quality Metrics

Compute true sigma (retrieval coverage) and rho (retrieval precision) from accumulated MemRL feedback, replacing proxy estimates.

## Usage

`/sigma-rho`

## Behavior

1. **Compute** — Call `hive_sigma_rho` to calculate metrics from feedback data.
2. **Interpret** — Explain the numbers:
   - **True sigma**: unique notes surfaced / total retrievable notes. Higher = broader coverage.
   - **True rho**: notes cited as helpful / notes surfaced. Higher = more precise retrieval.
   - **Escape velocity**: sigma * rho > delta/100. Above = knowledge compounds. Below = decay wins.
3. **Compare** — If `hive_health` data available, compare true metrics vs proxy estimates.
4. **Recommend** — Based on results:
   - Low sigma → more diverse searches needed, check for orphan clusters
   - Low rho → retrieval surfacing irrelevant notes, review tagging/linking
   - Below escape velocity → urgent: run `/health-check` for diagnosis

## Interpretation Guide

| sigma | rho | Status | Action |
|---|---|---|---|
| >0.3 | >0.5 | Healthy | Maintain current practices |
| >0.3 | <0.5 | Noisy retrieval | Improve tagging, prune stale notes |
| <0.3 | >0.5 | Precise but narrow | Link more notes to MOCs, diversify searches |
| <0.3 | <0.5 | Critical | Run `/health-check`, rebuild linking structure |

## MCP Tool

Primary: `hive_sigma_rho`
Supporting: `hive_health` (for comparison with proxy metrics)
