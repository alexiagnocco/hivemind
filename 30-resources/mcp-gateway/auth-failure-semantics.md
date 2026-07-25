---
created: 2026-06-10
updated: 2026-06-10
tags:
  - mcp
  - backend
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# Auth Failure Semantics

A backend that says "no" is answering. A backend that is down is not. Collapsing those two into one fallback path is how a tool ends up confidently serving stale data to a caller whose token expired — the silent wrong answer, which is the worst failure class a tool can have.

## The rule

- **4xx — especially 401 and 403 — surfaces to the caller. Always.** An auth or permission rejection is a real, actionable signal: the token is wrong, the scope is missing, the resource moved behind a policy. Masking it with a cache read or a filesystem fallback converts an actionable error into a plausible-looking answer that is wrong in a way nobody will notice for weeks.
- **5xx, timeouts, and connection failures are the only legitimate fallback triggers.** The backend didn't refuse — it failed to answer. A documented, deliberate fallback (cache, snapshot, degraded mode) is acceptable here on one condition: **the response announces it.** A fallback the caller can't see is indistinguishable from the real thing, and that invisibility is the bug.

```text
401/403  -> raise to caller, no fallback, ever
5xx/conn -> fallback allowed, response labeled "degraded: served from cache"
```

## Why teams get this wrong

The fallback usually exists first — built for resilience during an outage — and auth failures get routed into it later, by accident, because both look like "request failed" at the try/except. The fix is structural, not disciplinary: classify the failure *before* the fallback decision, and make the fallback branch unreachable for the 4xx class. This is the same classify-then-dispatch move that agent loops need generally; a caller consuming these errors should slot them straight into its own taxonomy.

## Degradation must stay visible end to end

The label has to survive the full path — server response, client tool result, agent observation — because a degraded answer that loses its label two hops downstream is silent again. Design the envelope so the degraded flag rides with the data ([[graceful-degradation-fallback-chains]] covers the chain-of-custody problem and why every fallback must be visible in the response).

Credential *resolution* failures deserve the same honesty: a server that silently starts with a missing token, then fails on first use, has just moved the 401 somewhere more confusing ([[credential-handling-in-mcp-servers]]).
