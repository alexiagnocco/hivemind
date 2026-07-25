---
created: 2026-06-06
updated: 2026-06-18
tags:
  - ai
  - optimization
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Context Budget Management

Keep the working context around 40% full. Past that, retrieval quality inside the window degrades — the model attends to less of what it holds — and every subsequent step pays the tax. Context is a budget, not a backpack.

## Load just-in-time, not just-in-case

The instinct is to front-load everything the agent *might* need. The result is an agent that starts every task already heavy: slower, more expensive, and more likely to anchor on an irrelevant document it was handed "for context." The discipline that works:

- **Anchor small.** One high-signal document up front — the project state, the task definition — and nothing else.
- **Retrieve on demand.** When the loop hits an unknown, fetch the specific thing. A targeted lookup beats a preloaded library every time; [[retrieval-quality-metrics]] is the evidence that coverage and precision are separable, and precision is what a busy window needs.
- **Summarize at boundaries.** Tool results enter the context as summaries with a pointer to the full payload, not as raw dumps. The loop rarely needs row 4,000 of the query result; it needs the shape and the count.

## Compaction is a feature, not a failure

Long-running agents must shed history to keep working. Treat compaction as a designed operation: decide what survives (decisions, open questions, invariants) and what evaporates (tool transcripts, superseded plans). An agent that compacts deliberately degrades gracefully; one that hits the wall mid-task loses state at an arbitrary point chosen by arithmetic instead of judgment.

Write the survivable state *outside* the context — a scratch file, a memory note — before you need it. Externalized state is also what makes [[checkpoint-restart-for-long-jobs]]-style resumption possible for agent work.

## Budget per step, not per session

A session budget hides the real constraint: each loop iteration needs headroom for the observation it is about to receive. Cap observation size at the tool boundary ([[plan-act-observe-loop-design]] treats this as a loop-design concern) and the per-step math stays predictable. Cache-aligned prompt structure ([[prompt-cache-alignment]]) then makes the tokens you do keep cheap to re-send.

The 40% number is a working default, not a law — but every agent I've profiled performed worse past it, and none performed better.
