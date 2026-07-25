---
created: 2026-06-12
updated: 2026-07-08
tags:
  - mcp
  - architecture
status: active
type: project
domain: work
seed: demo
---

# gateway-shim — Project Memory

Accumulated context for the gateway shim consolidation. Landing note: [[gateway-shim-consolidation]].

## Session Handoff — 2026-06-12

### What Was Done
- Shim skeleton running: namespacing and passthrough routing for the first two backing servers.
- Registry entries created for all seven backing servers with contract hashes captured at registration ([[mcp-server-registry-design]] pattern followed as written).
- Failure-class passthrough verified against the first server: forced 401 surfaces to the caller as 401 with the backing server named. This was the constraint most at risk of being "temporarily" violated during bring-up, so it went in first, with a contract test.

### Decisions Made
- Shim speaks streamable HTTP to clients; backing dev servers stay stdio behind adapter processes. Revisit only if adapter overhead shows up in traces.
- Namespace scheme: `<server>.<tool>` with no description rewriting — mechanical and lossless per [[ADR-001-mcp-gateway-shim]].
- Quota enforcement deferred to phase two; telemetry capture starts now so quota thresholds are set from observed usage, not guesses.

### Open Questions
- Two backing servers expose near-duplicate `search` tools with different result envelopes; consolidate behind one schema, or namespace and let callers choose? Leaning consolidate — two near-identical tools degrade model selection accuracy.

## Session Handoff — 2026-07-08

### What Was Done
- Integrations five of seven migrated; the two stragglers are the near-duplicate `search` pair (see open question above — still open, now blocking).
- Contract-hash check caught backing server four shipping a parameter-type change under an unchanged version string. Caught at registry refresh, before any client saw it. Wrote the incident up as validation of the hash design.
- Allowlist migration complete for migrated servers: the seven drifted client copies are down to two (the stragglers), with the shim policy as the single source for the rest.

### Decisions Made
- The near-duplicate `search` tools will be consolidated behind one schema at the shim (adapter maps to both backends). The alternative — exposing both namespaced — was rejected after a week of watching the model pick the wrong one in traces.
- Per-principal quotas ship with defaults at p95 of observed usage plus headroom.

### Open Questions
- Rollout of the consolidated `search` deserves its own canary window ([[canary-rollouts-for-agent-changes]]) since selection behavior changes for every client at once. Timing TBD.

### Next Session Start
- Implement the consolidated search adapter; canary it; migrate the final two integrations and retire the last client-side allowlists.
