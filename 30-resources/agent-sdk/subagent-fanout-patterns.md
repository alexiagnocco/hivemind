---
created: 2026-06-08
updated: 2026-06-15
tags:
  - ai
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Subagent Fan-Out Patterns

Fan out only for genuinely independent work. Parallel subagents buy wall-clock time and context isolation; they cost coordination, and the coordination cost is paid in defects you don't see until integration.

## When fan-out earns its overhead

- Three or more independent domains, files, or search spaces
- Each unit of work fits in a fresh context without the parent's history
- Results compose by concatenation or simple merge, not by negotiation

If the units share state, sequence them. If the answer is probably in one place, just look. A fan-out with two workers and a shared file is a race condition with extra steps.

## The brief is the product

Parallel workers cannot see each other. Everything they must agree on — counts, names, dates, schemas, conventions — exists in exactly one place: the shared brief. Pin every cross-file value verbatim in the brief, once; a value restated per-worker is where the second, contradictory version enters. Give each worker its file list, its boundaries ("touch nothing else"), and a self-checklist to run before returning, because long enumerations silently lose items.

## The audit pass is mandatory

Here is the part teams skip: after any fan-out that *writes*, run a single cross-cutting audit over the full changed set before declaring the work done. Per-worker verification proves presence; it structurally cannot prove consistency, because no worker holds two workers' output. The auditor catches cross-file contradictions, silently dropped brief clauses, and convention drift — the defect classes parallelism creates.

```text
workers 1..N (parallel, disjoint files)
        -> auditor (one pass, full changed set)
        -> integrate
```

## Failure handling

A worker returning thin results usually means the brief was vague, not that there was nothing to find — refine and rerun rather than retrying blind. A worker that dies mid-write leaves partial state: check the tree before rerunning, and design worker outputs so a rerun is idempotent, borrowing the same discipline tools owe callers in [[retry-idempotency-for-tool-calls]].

Fan-out is a loop-design decision, not an afterthought — the parent loop owns budgets and reconciliation ([[plan-act-observe-loop-design]]), and each worker's context starts near-empty by design ([[context-budget-management]]).
