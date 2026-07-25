---
created: 2026-06-30
updated: 2026-07-11
tags:
  - devops
  - optimization
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Rate Limit and Backoff Strategies

Jittered exponential backoff, circuit breakers on top, and one under-taught principle: retry budgets are *shared resources*. An agent system without a shared budget doesn't degrade under pressure — it self-amplifies, because every layer retries the layer below and the multiplication is silent.

## The baseline: exponential backoff with full jitter

```text
delay = random(0, min(cap, base * 2^attempt))
```

Full jitter, not equal or decorrelated — synchronized retries from parallel workers are a thundering herd you scheduled yourself. Respect `Retry-After` headers when the backend provides them; a server telling you when to come back is a gift, and overriding it with your own schedule is how polite clients get banned.

Classification comes first, though: backoff applies to environment errors — 429s, timeouts, 5xx. Retrying a 4xx rejection with backoff is patiently repeating a wrong question ([[error-taxonomy-for-agent-loops]] — the retry policy belongs to the class, and misclassification makes every policy wrong).

## The multiplication problem

Agent systems retry at multiple layers: the HTTP client, the tool wrapper, the loop step, sometimes the orchestrator re-running the task. Three retries at four layers is 81 potential attempts from one logical operation. The fix is a **retry budget** scoped to the task: layers *consume from* the shared budget instead of owning independent counters, and an exhausted budget fails the task with a classified error instead of borrowing more attempts. Budget exhaustion is also the natural alert point — it fires during the incident, not after ([[token-cost-observability]] applies the same task-scoped-budget logic to spend, and the two budgets often trip together).

## Circuit breakers: stop asking

Backoff protects the backend from *your* retries; breakers protect *you* from a dead backend. After N consecutive environment-class failures, open the circuit: fail fast, stop burning budget, probe with single requests until two succeed, then close. For agents the breaker has an extra virtue — a fast, classified "backend unavailable" lets the loop re-plan around the outage (use a fallback source, defer the step) instead of spending its step budget on hope. What the loop does with that fast failure is the fallback-chain design problem ([[graceful-degradation-fallback-chains]]).

Parallel fan-outs concentrate all of this: N workers share the downstream quota, so the budget must be partitioned *before* the spawn, not discovered at the 429.
