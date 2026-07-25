---
created: 2026-06-01
updated: 2026-06-03
tags:
  - ai
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Plan-Act-Observe Loop Design

The prompt gets all the attention, but the loop's termination conditions and step budgets determine whether an agent is shippable. Design those first; tune the prompt second.

A plan-act-observe loop is three decisions in a trench coat: what to try next, whether the last action worked, and whether to keep going. The third decision is where production agents fail. An agent with no explicit stopping rule will either quit early on a recoverable error or grind through forty steps of diminishing returns because nothing told it the marginal step stopped paying.

## Termination is a contract, not an emergent property

Pin three exits explicitly:

- **Goal check.** A concrete, evaluable success predicate — a test passes, a file exists, an API returns the expected shape. "The response looks done" is not a predicate. See [[structured-output-validation]] for making outputs checkable at the boundary.
- **Step budget.** A hard ceiling per task class. Budgets force the agent to fail loudly instead of wandering; a budget exhaustion is a *signal* you can alert on, an open-ended loop is not.
- **Stuck detection.** Same action, same observation, twice in a row means the loop is not converging. Break with a distinct error class per [[error-taxonomy-for-agent-loops]] so the caller can distinguish "stuck" from "failed."

## Budget the observation, not just the steps

Each observation competes for context with the plan. Raw tool output pasted into the loop is the most common self-inflicted wound; summarize or truncate at the boundary and keep the full payload addressable elsewhere, per [[context-budget-management]].

## What I'd do

Start every new agent with: goal predicate, step ceiling of 10, stuck detection at 2 repeats, and observations capped at a fixed token allowance. Loosen each limit only when a real transcript shows it binding for a legitimate reason. The transcript, not intuition, is the tuning instrument — which is also why traces matter more than dashboards early on.

Loops that fan work out to parallel workers push the same discipline down a level: each worker inherits a budget, and the parent owns reconciliation — see [[subagent-fanout-patterns]].
