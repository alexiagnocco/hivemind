---
created: 2026-06-04
updated: 2026-06-04
tags:
  - ai
  - architecture
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Agent-SDK]]"
seed: demo
---

# Structured Output Validation

Parsing prose out of a model response is a bug you chose. Constrain the output to a schema, validate at the boundary, and retry on failure — the combination is cheaper and more reliable than any regex you will ever write against free text.

## Validate where the data crosses the boundary

The pattern is three moves:

1. **Declare the schema** — JSON Schema or a typed equivalent — and pass it to the model as a constraint, not a polite request buried in the prompt.
2. **Validate mechanically** on receipt. The validator, not the model, is the authority on conformance.
3. **Retry with the error** on failure. Feed the validator's message back verbatim; models correct schema violations well when told exactly what failed, and badly when told "try again."

Two retries is the practical ceiling. A model that fails the same schema three times is telling you the schema and the task disagree — usually a field the model has no way to know, or an enum missing the value the task actually produces. That is a design signal, not a retry problem.

## Schema design notes that earn their space

- **Make illegal states unrepresentable.** If two fields are mutually exclusive, model that as a union, not a comment.
- **Required means required.** Optional fields accumulate silently-null garbage; require what you consume, drop what you don't.
- **Bound your arrays.** An unbounded list invites the model to pad. `maxItems` is a quality control, not a formality.

## The boundary is also your regression surface

Validated outputs are what make agent behavior testable: pin a known-good structured output for a fixed input and you have a regression check that survives wording drift — the mechanics are in [[regression-pinning-evals]]. Unstructured outputs can only be eyeballed, and eyeballs don't run in CI.

The same discipline applies on the input side of every tool call ([[tool-calling-contracts]]), and the error classes a failed validation emits should slot into the loop's taxonomy ([[error-taxonomy-for-agent-loops]]) so the caller can tell a malformed output from a wrong one. Malformed is retryable; wrong is a task failure.
