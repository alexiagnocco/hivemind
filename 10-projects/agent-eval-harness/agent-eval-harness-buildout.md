---
created: 2026-06-16
updated: 2026-07-16
tags:
  - testing
  - ai
status: active
type: project
domain: work
project: agent-eval-harness
priority: medium
seed: demo
---

# Project — Agent Eval Harness Buildout

Stand up a regression eval suite that gates agent changes in CI: graded task fixtures, pinned baselines, and a merge gate that blocks on deltas — so prompt edits stop shipping as if they were copy changes.

## Why

Agent behavior changes were reaching production through PRs that looked like one-line string edits. No fixture caught them because no fixtures existed; the first signal was users noticing. The suite converts "did this change behavior?" from a review-time guess into a mechanical answer — the design principles are in [[eval-suite-design-for-agents]], and the gating mechanics in [[regression-pinning-evals]].

## Decision record

[[ADR-002-eval-gating-in-ci]] (accepted 2026-06-18): eval regressions block merges; nightly-only evals rejected because the feedback loop is too slow to assign blame to a specific diff. The gate runs the full graded suite on every behavior-touching PR.

## Scope

- Task fixtures for the top task classes, frozen environments, versioned with the suite
- Rubric-graded scoring with binary per-criterion checks; judge-graded criteria calibrated against a human-labeled set ([[llm-as-judge-caveats]] drove the binary-criteria decision)
- Pinned baseline artifacts in-repo, updated only via reviewed PRs
- CI wiring: delta report as a PR comment, hard block on criterion regressions
- Flake quarantine with a visible count ([[quality-signal-dashboards]] tracks it)

Out of scope for this phase: online canary tooling — the offline/online split and its sequencing rationale are in [[offline-vs-online-agent-evals]].

## Status

Gate live on the two highest-traffic agents. First month: three real regressions blocked, one flaky pin quarantined and tightened. Handoffs, decisions, and open questions: [[memory/projects/agent-eval-harness]].
