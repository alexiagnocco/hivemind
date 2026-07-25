---
created: 2026-06-21
updated: 2026-07-03
tags:
  - testing
  - devops
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Agent Tracing Instrumentation

One span per tool call, token counts on every span, and a sampling strategy decided before the incident — not during it. Agent observability is ordinary distributed tracing plus two twists: the interesting state is text, and the costs are per-token.

## The span model

Trace = one task. Under it: a span per loop iteration, a span per tool call, a span per model request. Every model-request span carries input tokens, output tokens, cached tokens, and latency; every tool span carries the tool name, argument digest, result size, and error class if any ([[error-taxonomy-for-agent-loops]] gives the class vocabulary — recording it structured is what makes error-rate-by-class a one-line query).

The twist: spans reference *artifacts*, not payloads. Full prompts and observations go to blob storage, content-addressed; the span holds the hash and the first line. Traces stay queryable and cheap; the payload is one dereference away when you need the actual words — the same indirection discipline tools should apply to their own oversized results ([[tool-result-size-management]]).

## Sampling: decide the policy in peacetime

Token accounting makes full tracing affordable; payload storage does not. The policy that works:

```text
metadata spans:        100% (always)
payload retention:     100% for failures and gated actions,
                       N% random sample of successes,
                       always-on for canary cohorts
```

Failures keep everything because incident review needs the words. Successes sample because aggregate statistics need volume, not verbatims. Canary cohorts trace fully because a rollout under evaluation is exactly when you want replayable evidence ([[canary-rollouts-for-agent-changes]]).

## Traces feed everything downstream

Instrumentation is the substrate, not the product. Cost attribution is a group-by over span token fields ([[token-cost-observability]]); dashboards are aggregations over span outcomes ([[quality-signal-dashboards]]); failed production traces, replayed against fixtures, are your best source of new eval tasks. The teams that skip tracing don't skip the questions — they just answer them by guessing.

Retention closes the loop: keep failure payloads long enough to survive the incident review cycle, and expire success payloads aggressively. Text is heavy, and yesterday's happy transcript has almost no marginal value.
