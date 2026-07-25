---
name: ai-engineer
description: "LLM application engineering playbook: RAG, agents, prompt and context engineering, tool use, structured outputs, and evals. Use this skill whenever the user wants to build, design, review, or debug anything LLM-powered, even if they never say 'AI' — trigger on phrases like 'add retrieval', 'semantic search', 'chat over our docs', 'the model keeps hallucinating', 'agent workflow', 'function calling', 'tool calling', 'improve this prompt', 'measure LLM quality', or 'which model should I use'. Also use when deciding between RAG, long context, and fine-tuning, or between a workflow and an autonomous agent."
---

# AI Engineer Playbook

Decision frameworks and checklists for LLM application work. Use these to make defensible architecture choices and to avoid the two most common failure modes: over-building (agent where a workflow suffices) and vibe-iterating (changing prompts with no eval).

## When to delegate to the `ai-engineer` subagent

Spawn the `ai-engineer` subagent instead of working inline when the task is any of:

- Multi-file implementation (new RAG pipeline, agent loop, eval harness)
- Long-running eval or benchmark execution
- Research-heavy design work (comparing embedding models, retrieval strategies)
- Retrieval-quality debugging that requires inspecting many chunks/queries

Reason: this work generates noisy intermediate output. Isolating it in a subagent keeps the main conversation's context clean, and the parent receives only the decision record. For quick questions, single-file edits, or reviewing a design, stay inline and use the frameworks below directly.

## The architecture ladder

Always start at the lowest rung that could work. Move up one rung only when a **measured** failure demands it.

1. **Single LLM call** — one well-engineered prompt, possibly with retrieved context and few-shot examples. Covers a surprising majority of use cases.
2. **Workflow** — deterministic code orchestrates multiple LLM calls. Pick the matching pattern:
   - *Prompt chaining*: fixed sequence, each step's output feeds the next (draft → critique → revise).
   - *Routing*: classify the input, dispatch to a specialized prompt/model per category.
   - *Parallelization*: independent subtasks fan out, results aggregate (sectioning) — or same task runs N times for consensus (voting).
   - *Orchestrator-workers*: an LLM decomposes the task dynamically and delegates to workers when subtasks can't be predicted upfront.
   - *Evaluator-optimizer*: generator loop with an LLM grader providing feedback until criteria pass.
3. **Autonomous agent** — LLM in a loop choosing its own tools and steps. Justified only when the path genuinely cannot be predicted and the environment provides feedback (test results, tool errors) the model can react to.

If someone asks for an "agent," first check whether rung 2 solves it. Workflows are cheaper, faster, and debuggable.

## Knowledge strategy: stuffing vs. RAG vs. fine-tuning

| Situation | Choice | Why |
|---|---|---|
| Corpus fits comfortably in context, changes rarely | Prompt stuffing / cached context | Zero infrastructure; prompt caching makes repeated use cheap |
| Corpus is large, changes often, or answers need citations | RAG | Retrieval scopes context to what's relevant; citations fall out naturally |
| Need consistent style, format, or domain vocabulary | Fine-tuning | Fine-tuning teaches *behavior*, not *facts* — it is the wrong tool for knowledge injection |

Default to the first row until it measurably fails.

## RAG checklist

Work through these in order — retrieval problems upstream make everything downstream look broken.

1. **Corpus prep**: normalize formats, strip boilerplate, preserve document structure (headings, tables) — structure-aware chunking beats fixed-size splitting.
2. **Chunking**: start with structure-aware chunks (section-level), ~200–800 tokens, with document-title and section-path metadata attached. Treat sizes as starting points to tune against retrieval evals, not constants.
3. **Retrieval**: hybrid (BM25/keyword + dense embeddings) with a reranker outperforms either alone on most corpora. Add metadata filters (date, domain, doc type) before semantic search when the query implies them.
4. **Staleness**: decide explicitly how archived/superseded content is handled (filtered out, down-weighted, or labeled) — silent staleness is a top source of "the bot is wrong" reports.
5. **Evaluate retrieval separately from generation**:
   - Retrieval: recall@k, MRR against a labeled query→relevant-chunk set.
   - Generation: groundedness (is every claim supported by retrieved context?) and citation accuracy.
   A great generator cannot fix a retriever that never surfaces the answer.

## Agent checklist

- **Tool design**: descriptive names, narrow parameter schemas, docstrings written for the model, and error messages the model can act on ("file not found: did you mean X?" beats a stack trace).
- **Stop conditions**: max turns, max cost, timeout — all three, always.
- **Human gates**: any irreversible or externally visible action (writes, sends, deletes, purchases) requires confirmation or runs in a sandboxed/dry-run mode first.
- **State**: plan for context compaction on long runs; persist durable state outside the context window.
- **Observability**: log every tool call with inputs, outputs, tokens, and latency. An agent you can't replay is an agent you can't debug.

## Eval discipline

- Build the first eval set from **real failures and real usage**, not synthetic guesses. 10–30 cases is enough to start; grow it as new failures appear.
- Grader hierarchy, strongest first:
  1. **Code assertions** (exact match, schema validation, contains/regex, numeric tolerance) — deterministic, free, use whenever possible.
  2. **LLM-as-judge with a written rubric** — for subjective qualities; never let the judge be the same prompt/config as the generator it grades.
  3. **Human review** — reserve for what the above can't measure.
- Run evals on every meaningful change and record results alongside the change. "It seems better" is not a result.

## Prompt & context engineering quick rules

- State instructions positively and specifically; examples beat adjectives ("respond like Example 1" beats "be concise and professional").
- Use few-shot examples to lock output *format*; use structured outputs / tool schemas when a machine consumes the result.
- Put stable content (system prompt, reference docs) in cache-friendly positions; put volatile content last.
- Audit context bloat periodically: measure tokens per request and ask what each block is buying you.

## Anti-patterns (name them when you see them)

- **Framework-first**: reaching for an orchestration framework before a direct API call has been tried.
- **Agent-when-workflow-suffices**: rung 3 chosen for predictable, decomposable tasks.
- **Vibe-climbing**: iterating on prompts with no eval set and no baseline.
- **Mega-prompt**: one prompt handling routing, generation, and validation — split it.
- **Self-grading**: the generator's own prompt used as the judge of its output.
- **RAG-on-a-pamphlet**: retrieval infrastructure for a small static corpus that fits in context.

## Reference files

Deep-dive material lives in `references/`. Load only what the task needs:

- **`references/rag-patterns.md`** — read when designing or debugging retrieval: chunking recipes, embedding selection, hybrid + reranker stack, query handling, retrieval eval setup, staleness strategies.
- **`references/agent-patterns.md`** — read when building a rung-3 agent or orchestrator-workers workflow: tool schema design, the loop template with stop conditions, human gates, state/compaction, observability, handoff contracts.
- **`references/eval-design.md`** — read when building an eval harness or grading a change: eval-set curation, code grader library, LLM-judge rubrics and calibration, reporting discipline.

The checklists above are sufficient for design discussions; open the reference file before implementing.
