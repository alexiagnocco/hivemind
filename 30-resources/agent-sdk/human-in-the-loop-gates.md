---
created: 2026-06-16
updated: 2026-06-19
tags:
  - ai
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Human-in-the-Loop Gates

Gate on reversibility, not on confidence. A model's self-reported confidence is uncalibrated and ungameable in the wrong direction; whether an action can be undone is a property of the *action*, and you can enumerate it ahead of time.

## The reversibility tiers

- **Freely reversible** — reads, drafts, scratch writes, anything in a sandbox. No gate. Gating these teaches humans to rubber-stamp, which destroys the gate's value everywhere else.
- **Reversible with effort** — file edits under version control, config changes with rollback. Gate by policy: autonomous inside an approved task scope, prompted outside it.
- **Hard or impossible to reverse** — external sends, deletes, payments, anything that publishes or notifies. Always gate. No accumulated trust, no "the last five were fine." The sixth is the incident.

The tier boundaries belong in the same place as tool permissions — enforced at the boundary, not requested in the prompt. A prompt-level "please ask before deleting" is a wish; a permission tier on the delete tool is a control. Sizing those tiers to worst-case rather than intended use is the subject of [[blast-radius-limits-for-tools]].

## Interrupts must be cheap for the human

A gate that costs the human ten minutes of context reconstruction will be bypassed within a month, by the human. Design the interrupt like an API:

- Present the exact action, its target, and its blast radius — not the transcript that led there.
- Offer real options (approve, modify, reject) with a recommended default.
- Batch related approvals; five sequential prompts for one logical change is nagging, and nagging trains dismissal.

## Approval is context-bound

An approval authorizes one action in one context. Reusing it — "the user approved a push earlier, so push again" — is how automation quietly exceeds its mandate. Expire approvals with the task, and log every gate decision in the audit trail so the trace of *who authorized what* survives the session ([[incident-response-for-agent-systems]] treats that trail as an operational requirement, not a compliance nicety).

Gates compose with loop design: a step budget stops runaway loops, a gate stops runaway *authority*. The two failure modes are different, and each needs its own mechanism ([[plan-act-observe-loop-design]]).
