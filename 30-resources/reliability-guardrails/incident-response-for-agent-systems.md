---
created: 2026-07-04
updated: 2026-07-15
tags:
  - devops
  - automation
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Incident Response for Agent Systems

Kill switches, audit trails, and runbooks — written before the first incident, because during it you will be too busy discovering that you needed them. Agent incidents differ from service incidents in one essential way: the system was *acting*, not just serving, so response means stopping intentions mid-flight and reconstructing what was done on whose authority.

## Kill switches, plural and tiered

One global off-switch is necessary and insufficient. The useful set:

```text
per-tool:    disable one capability everywhere (the leaking integration)
per-agent:   stop one agent class, leave the rest running
per-tier:    freeze all irreversible actions, keep reads flowing
global:      everything stops; the break-glass option
```

Requirements: seconds to take effect, no deploy in the path, and an owner who can pull each switch without a meeting. The per-tier freeze is the workhorse — most agent incidents warrant "stop *changing* things" rather than "stop everything," and a tiered permission model makes that a one-flag operation ([[blast-radius-limits-for-tools]] provides the tiers; the switch just flips one).

## The audit trail answers three questions

Who authorized it, what did it touch, and what was it *trying* to do. The trail that answers them: every gate decision with its approver and context ([[human-in-the-loop-gates]] logs these as a matter of course), every mutation with its effect identity, every task with its goal. Full tracing makes this nearly free — the incident view is a filtered trace query, with payloads retained for exactly the failure cases you now need to read ([[agent-tracing-instrumentation]]'s retention policy earns its keep here).

The reconstruction question incident commanders actually ask: "what did the agent do that *hasn't been noticed yet*?" An effect ledger queryable by time window and tool tier is the difference between an answer and a sweep of every system the agent could reach.

## Runbooks for the three agent-incident shapes

1. **Runaway** — loop burning budget or hammering a backend. Response: per-agent switch, then budget forensics.
2. **Bad actions** — agent doing wrong things confidently. Response: tier freeze, effect-ledger sweep, compensation of unwound mutations (the cleanup obligations of [[cancellation-semantics-for-agent-jobs]], executed late).
3. **Bad answers** — quality collapse without bad actions, often a silent degradation or an unflagged model change. Response: cohort comparison on the dashboard, then rollback of the last behavioral deploy ([[canary-rollouts-for-agent-changes]]'s hot rollback is the recovery path).

Post-incident, the transcripts become fixtures — every incident should make the offline suite smarter, or it will reprise.
