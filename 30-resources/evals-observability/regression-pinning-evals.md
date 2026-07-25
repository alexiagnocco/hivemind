---
created: 2026-06-19
updated: 2026-06-19
tags:
  - testing
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# Regression Pinning Evals

An unpinned eval is a vibe. The suite that protects you is the one where known-good outputs are frozen as artifacts, every change is scored as a delta against them, and the merge gate is mechanical: regress the pin, block the merge, no negotiation in the moment.

## What a pin actually is

A pin is a tuple: fixed input, frozen environment fixture, the accepted output (or its graded score profile), and the date and rationale of acceptance. The rationale matters — six months later, "why is this the golden answer" is otherwise archaeology. Store pins in the repo next to the suite; they are code-review-able artifacts, and a change to a pin is a *decision*, reviewed like one.

Pin score profiles rather than raw text wherever grading is rubric-based: text pins break on harmless rewording, which trains everyone to rubber-stamp pin updates — and a rubber-stamped pin protects nothing. Structured outputs are the friendliest surface to pin, which is an argument for schema-constrained agent boundaries in general ([[structured-output-validation]] makes the case from the design side).

## Gate on deltas, not absolutes

"Score must exceed 0.8" rots as the suite grows and tasks shift in difficulty. "No criterion regresses versus baseline, and total drops by less than X" stays meaningful indefinitely. Deltas also localize blame: the diff that turned a criterion red is in the PR you are reviewing, not somewhere in last quarter.

Run the gate on every change that can alter behavior — prompts, tools, model version, retrieval config. Prompt edits especially: they look like copy changes and ship like copy changes, but they are behavior changes wearing a disguise ([[canary-rollouts-for-agent-changes]] applies the same insight post-merge).

## Maintaining pins without drowning

- **Intentional improvements** produce pin updates in the same PR, with the delta visible to the reviewer.
- **Flaky pins** — same input, oscillating verdicts — are quarantined, counted, and fixed by tightening the task or the rubric, never by widening tolerance silently. Flake count is itself a quality signal worth charting ([[quality-signal-dashboards]]).
- **Judge-graded pins** inherit every judge instability; keep pinned criteria as mechanical as possible ([[llm-as-judge-caveats]]).

The suite these pins live in is designed in [[eval-suite-design-for-agents]]; pinning is the part that turns it from a dashboard into a brake.
