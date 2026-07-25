---
created: 2026-06-18
updated: 2026-06-20
tags:
  - ai
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Error Taxonomy for Agent Loops

Tool errors, model errors, and environment errors are three different animals, and a loop with one undifferentiated retry policy handles all three wrong. The taxonomy is small; the payoff is that every error maps to exactly one response.

## The three classes

**Tool errors** — the tool ran and said no. Validation rejections, not-found, permission denied, business-rule violations. The tool is *answering*; retrying the identical call is asking the same question louder. The correct response is to change the arguments or change the plan. A 4xx-style rejection that gets blindly retried is the signature of a loop missing this class.

**Model errors** — the model produced something unusable. Malformed structured output, a call to a nonexistent tool, an argument type mismatch. These are retryable *with feedback*: return the validation failure verbatim and let the model correct ([[structured-output-validation]] covers the mechanics and the two-retry ceiling).

**Environment errors** — the substrate failed. Timeouts, connection resets, rate limits, out-of-disk. The tool never answered. These are retryable *with backoff*, and they are the only class where a retry of the identical call is correct — which is exactly why mutating tools need the idempotency guarantees in [[retry-idempotency-for-tool-calls]] before that retry is safe.

## Why the classification must be machine-readable

The loop cannot read prose. Tools must return errors in a structured envelope with the class explicit:

```text
{"error": {"class": "tool_rejection", "code": "not_found", "retryable": false}}
```

An error message written for humans forces the model to *infer* the class, and it will infer wrong at the worst moment. Making the class a field turns error handling from interpretation into dispatch.

## Escalation is part of the taxonomy

Each class has an exhaustion behavior: tool rejections escalate to plan revision; model errors exhaust after two feedback retries; environment errors exhaust after the backoff budget. Exhaustion terminates the step with a classified failure the caller can route — to a human gate, an incident path, or a graceful skip ([[plan-act-observe-loop-design]] treats these exits as first-class loop design). Timeouts deserve one refinement: classify slow-but-succeeding separately from dead, or you will cancel work that was about to finish.
