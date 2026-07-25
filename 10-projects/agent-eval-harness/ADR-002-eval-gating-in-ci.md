---
created: 2026-06-18
updated: 2026-06-18
tags:
  - architecture
  - testing
status: active
type: decision
domain: work
decision: accepted
context: "Prompt and tool changes shipping as unreviewable one-line diffs with no behavioral check"
seed: demo
---

# ADR-002 — Block Merges on Eval Regression Deltas

**Status:** accepted, 2026-06-18

## Context

Behavior-changing edits — prompts, tool descriptions, retrieval config — ship through PRs that read as trivial string changes. Review cannot see behavior in a diff. Three user-visible regressions in one quarter traced back to merges nobody flagged, and in each case the offending diff was under five lines.

## Decision

CI runs the graded eval suite on every PR that touches behavior-bearing paths (prompts, tool schemas, retrieval config, model pins). The gate is delta-based against the pinned baseline: any per-criterion regression blocks the merge; total-score drops beyond threshold block the merge. Pin updates ride in the same PR as the change that justifies them, so the reviewer sees the behavioral delta next to the code delta ([[regression-pinning-evals]] specifies the pin format and maintenance rules).

## Alternatives considered

**Nightly eval runs with alerting (rejected).** Cheaper per-PR, but the feedback loop is too slow to assign blame: a red nightly implicates a day of merges, and the investigation cost lands on whoever notices rather than whoever caused it. Gates put the cost on the author at the moment the context is loaded.

**Manual eval invocation by authors (rejected).** Relies on authors recognizing their change as behavioral — and the motivating incidents were precisely failures of that recognition.

**Full suite on every commit (deferred, not rejected).** Cost currently unjustified; path-filtered triggering covers the observed regression sources. Revisit when suite runtime drops.

## Consequences

PR latency increases by the suite runtime — accepted, and it creates sustained pressure to keep the suite fast, which is healthy. Flaky pins become merge-blockers for innocent PRs, so the flake-quarantine process is part of this decision, not an optional nicety. The gate's blind spot is distribution drift — a green gate on a stale suite is false comfort — so drift monitoring runs alongside ([[eval-drift-detection]]). Buildout is tracked in [[agent-eval-harness-buildout]].
