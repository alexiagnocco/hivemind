---
created: 2026-07-24
updated: 2026-07-24
tags:
  - meta
status: active
type: reference
domain: meta
seed: demo
---

# Demo Corpus README

This knowledge base ships with a seeded demonstration corpus so that hivemind's subsystems have something real to work on the moment you clone the repo — retrieval returns ranked results, the link graph has structure, MOCs map actual content, and health metrics compute against a live corpus instead of an empty scaffold.

## What is and isn't real

Every note in this knowledge base marked `seed: demo` is synthetic demonstration content, written to show hivemind's retrieval, linking, and health subsystems operating on a realistic corpus. The projects, decisions, dates, and session handoffs described in these notes are fictional. Anything not marked `seed: demo` — the engine, the skills, the hooks, and their test results — is real.

The corpus is themed to agent-platform engineering (agent loops, MCP servers and gateways, evaluation, reliability) because that is the domain this system itself lives in — the notes double as a readable tour of the engineering thinking behind hivemind.

## The shape of the corpus

Four content domains, each mapped by a MOC:

- [[MOC-Agent-SDK]] — loop design, tool contracts, context economics (10 notes)
- [[MOC-MCP-Gateway]] — server design, failure semantics, deployment (10 notes)
- [[MOC-Evals-Observability]] — eval suites, judges, tracing, cost (10 notes)
- [[MOC-Reliability]] — containment, rollouts, checkpointing, incidents (8 notes)

Plus a system layer that exercises the hive's other surfaces: two fictional projects with landing notes ([[gateway-shim-consolidation]], [[agent-eval-harness-buildout]]) and project memories, three ADRs, a [[memory/glossary|glossary]], and two unprocessed inbox captures ([[idea-tool-timeout-taxonomy]], [[2026-07-18-meeting-gateway-rollout-review]]) left there deliberately so `/process-inbox` has something to triage.

`30-resources/synthesis/` ships empty on purpose — run `/connect` to watch synthesis notes generated live from the cross-domain links in this corpus.

## Filtering it out

Every seeded file carries `seed: demo` in its frontmatter. To query only your own content once you start writing, filter on the absence of that field; to remove the corpus entirely, delete every file that carries it — the engine does not depend on the corpus in any way.
