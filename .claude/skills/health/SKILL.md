---
description: "Quick knowledge health metrics from the knowledge compounding equation"
---

# /health — Knowledge Health Metrics

Compute knowledge health metrics from the knowledge compounding equation. This is the metrics engine — for a full diagnostic with recommendations, use `/health-check`.

## Usage

`/health` · `/health --window 14` · `/health --stale 60`

## Behavior

1. **Compute** — Call `hive_health` with window_days (default 7) and stale_threshold_days (default 30).
2. **Display metrics**:
   - **K** (knowledge stock): total active, linked, non-stale notes
   - **I(t)** (input rate): notes created/modified in the measurement window
   - **delta** (decay rate): fraction of notes going stale
   - **sigma** (retrieval coverage): fraction of notes reachable via search/links
   - **rho** (retrieval precision): fraction of retrieved notes with citations
   - **phi** (scale factor): diminishing returns as hive grows
   - **Escape velocity**: sigma * rho > delta/100 — is knowledge compounding?
   - **dK/dt estimate**: net knowledge growth rate
3. **Interpret** — Traffic light status:
   - THRIVING: escape velocity met, positive dK/dt
   - STABLE: escape velocity met, flat dK/dt
   - DECAYING: below escape velocity, negative dK/dt
4. **Compare** — If previous health data exists in `_meta/hive-health.md`, show trend arrows.

## vs /health-check

| Feature | /health | /health-check |
|---|---|---|
| Speed | Fast — single MCP call | Slower — full scan |
| Output | Metrics only | Metrics + orphans + broken links + recommendations |
| Action items | Interpretation only | Specific fix-it list |
| Use case | Quick pulse check | Full diagnostic |

## MCP Tool

Primary: `hive_health`
