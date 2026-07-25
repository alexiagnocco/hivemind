---
created: 2026-06-12
updated: 2026-06-20
tags:
  - ai
  - retrieval
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Agent Memory Architectures

Bigger context windows keep losing to better retrieval. The useful frame is three memory tiers with different lifetimes and access patterns — and the design work is deciding what lives where, not maximizing any single tier.

## The three tiers

- **Working memory** — the context window. Fast, expensive, evaporates at session end. Holds the current task, the active plan, and recent observations. Managed by budgeting and compaction ([[context-budget-management]]).
- **Episodic memory** — what happened. Session logs, handoffs, decision records. Append-only, time-stamped, queried by "what did we do about X." Its value decays unless distilled: an un-mined transcript is a landfill, not a memory.
- **Semantic memory** — what we know. Durable notes, patterns, and reference material, organized for retrieval rather than recency. This is the tier that compounds: every session can deposit into it and every future session can draw from it.

## Retrieval-augmented loops beat bigger windows

Stuffing semantic memory into working memory "so it's available" is the most common architecture mistake. It spends the scarcest resource on speculation. The loop that works: start near-empty, retrieve on demand against the semantic store, and let a scoring function — not chronology — decide what surfaces.

The scoring function is where the interesting engineering lives. Recency and keyword match are table stakes; link-graph connectivity adds structure; and a learned utility signal — rewarding notes that, once retrieved, actually got *used* — closes the loop. Retrieval that learns from its own citations gets measurably sharper over time; the feedback mechanics are covered in [[feedback-loops-for-ranking]].

## Write path matters as much as read path

A memory architecture with a great retriever and no deposit discipline starves. Persist decisions when they happen, not at session end; distill episodic logs into semantic notes on a cadence; and link every new note into the graph so it is reachable by more than keyword luck. An unlinked note is invisible at retrieval time — which is functionally identical to never having written it.

Termination and step budgets interact with memory too: a loop that ends by writing its handoff ([[plan-act-observe-loop-design]]) is the loop that starts warm tomorrow.
