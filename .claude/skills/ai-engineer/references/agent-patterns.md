# Agent Patterns

Deep-dive reference for the `ai-engineer` skill. Read this when building rung-3 systems (autonomous loops) or the orchestrator-workers workflow pattern. Confirm first, via the architecture ladder in SKILL.md, that a workflow won't suffice.

## 1. Tool design

Tools are the agent's UI. Most agent failures trace back to tool design, not model capability.

- **Names**: verb-first, unambiguous, one job per tool. `search_tickets` + `get_ticket` beats a `tickets` tool with a `mode` param.
- **Parameters**: narrow schemas with enums and formats spelled out. Every optional param is a decision the model can get wrong — default aggressively.
- **Docstrings are prompts**: write the description for the model, not for developers. State when to use it, when NOT to use it, and one example call. This text is what the model actually reads.
- **Error messages the model can act on**: return `"date must be YYYY-MM-DD, got '6/1/26'"` — never a bare stack trace or error code. A good error string is a self-healing loop; a bad one is a wasted turn.
- **Idempotency**: retries happen. Make mutating tools idempotent (accept a client-generated request id) or split into `prepare_x` (safe) + `commit_x` (gated).
- **Token-aware returns**: cap and paginate tool output. A tool that dumps 40k tokens of JSON destroys the context budget; return summaries with ids the model can drill into.

## 2. The loop template

Minimum viable agent loop with all three stop conditions:

```python
def run_agent(task: str, tools: list, max_turns=15, max_cost_usd=2.00, timeout_s=300):
    ctx = [system_prompt, user(task)]
    spent, t0 = 0.0, time.monotonic()

    for turn in range(max_turns):                      # stop 1: turns
        if spent >= max_cost_usd:                      # stop 2: budget
            return fail("budget exceeded", ctx)
        if time.monotonic() - t0 > timeout_s:          # stop 3: wall clock
            return fail("timeout", ctx)

        resp = llm(ctx, tools)                         # log: model, tokens, latency
        spent += cost_of(resp)

        if resp.stop_reason == "end_turn":             # model says done
            return success(resp, ctx)

        for call in resp.tool_calls:
            if is_irreversible(call) and not human_approved(call):   # human gate
                return pause_for_approval(call, ctx)
            result = execute(call)                     # log: name, args, result, ms
            ctx.append(tool_result(call.id, result))
```

Notes:

- All three stop conditions, always — any one alone has a failure mode that burns money or hangs.
- On `max_turns`, return partial state and what was attempted, not a bare failure — the parent (or human) can often finish from there.
- Log every LLM call and tool call inline (see §5); retrofitting observability onto a live agent is miserable.

## 3. Human gates and permission tiers

Classify every tool once, at design time:

| Tier | Examples | Policy |
|---|---|---|
| **Read** | search, get, list | Auto-execute |
| **Reversible write** | draft file in workspace, create branch, add comment | Auto-execute, log loudly |
| **Irreversible / externally visible** | send email, merge, delete, purchase, prod deploy | Human confirmation or dry-run mode; never auto |

Dry-run mode: irreversible tools accept `dry_run=True` and return what *would* happen. Lets the loop plan end-to-end while a human approves only the final commit step.

## 4. State and context management

- **Externalize durable state**: task list, decisions made, artifacts produced live in files or a store — not only in the transcript. The context window is a cache, not a database.
- **Compaction**: on long runs, periodically replace old turns with a structured summary (goal, decisions, open items, file paths touched). Trigger on token threshold (~60–70% of window), not turn count.
- **Scratchpad pattern**: give the agent a `notes.md` it owns for intermediate reasoning/results. Survives compaction and makes runs auditable.
- **Fresh-context handoff**: for multi-phase work, ending a phase with a written handoff doc + starting a clean context often beats one marathon context. Noise compounds.

## 5. Observability

Log per LLM call: model, input/output tokens, latency, stop reason. Log per tool call: name, args, result size, duration, error. Attach a run id to everything.

The bar: **any run can be replayed from logs alone.** If you can't reconstruct why the agent did something, you can't debug it, and you can't build an eval case from the failure (see `eval-design.md` §1 — production failures are your best eval source).

## 6. Orchestrator-workers handoff contract

When one agent delegates to sub-workers (or a Claude Code main thread delegates to subagents):

- Workers receive a **task brief** (goal, constraints, relevant file paths, output contract) — not the parent's transcript.
- Workers return a **structured summary** (decision record, artifacts produced, open risks) — not their transcript. The paired `ai-engineer` subagent's output contract is an example of this.
- Parallelize only workers that don't write to the same files/state; serialize anything with write conflicts.
- The orchestrator, not the workers, owns integration: it verifies worker outputs compose (run the tests, check the interfaces) before reporting success upward.
