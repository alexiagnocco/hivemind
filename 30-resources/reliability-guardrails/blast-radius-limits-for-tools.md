---
created: 2026-06-28
updated: 2026-07-08
tags:
  - devops
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Reliability]]"
seed: demo
---

# Blast Radius Limits for Tools

Size every tool's permissions to its worst-case misuse, not its intended use. Intent lives in the prompt; the prompt is a suggestion. The permission tier is the only part of the system that holds when the model is wrong, confused, or manipulated — which is to say, the only part that is actually a guardrail.

## The tiering model

```text
tier 0: reads, queries, dry-runs          -> unrestricted
tier 1: reversible writes, scoped paths   -> allowed within task scope
tier 2: external sends, deletes, publish  -> gated, always
```

Assign by *worst case*: a "send message" tool is tier 2 even when the intended recipient is a test channel, because the worst case is every channel it can reach. A file-write tool scoped to a sandbox directory is tier 1; the same tool with filesystem-wide reach is tier 2 wearing a smaller tool's name — the scope, not the verb, sets the tier.

Enforce at the boundary, not in the prompt. "Please don't delete production data" is documentation; a tool that *cannot address* production data is a control. Path allowlists, principal scoping, and rate caps live in the tool contract itself ([[tool-calling-contracts]] — the contract is where enforcement and documentation converge, and an unenforced limit is neither).

## Dry-run modes are cheap insurance

Every tier 1-2 tool should offer a dry-run that returns *what would happen* — files to be touched, records to be deleted, recipients to be messaged. Agents can then plan against previews and escalate only the real execution. Dry-runs also make gate prompts meaningful: a human approving "delete 3 files: a, b, c" is consenting to something specific; a human approving "run cleanup" is signing a blank check ([[human-in-the-loop-gates]] — the gate is only as informed as the preview behind it).

## Sandboxes convert tiers downward

Work performed in an isolated copy — a worktree, a staging namespace, a scratch schema — downgrades tier 2 verbs to tier 1, because the blast radius is the sandbox boundary. The pattern: let the agent operate freely inside the sandbox, then gate the single *release* step that moves results into the real world. One gate on the exit beats ten gates on the interior.

Rate caps complete the picture: even tier 0 reads deserve a budget, because a runaway loop hammering a read API is its own small incident ([[rate-limit-backoff-strategies]]). When the limits do fire, that event belongs in the audit trail — limit-hits are the early telemetry of an agent operating outside its envelope ([[incident-response-for-agent-systems]]).
