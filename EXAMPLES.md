# Examples

End-to-end walkthroughs of the core loops. These assume the `hivemind` MCP server is registered (see [README](README.md)) and the hive holds real engineering notes.

## 1. A normal work session: boot → work → wrap

```text
> /boot
--- Session ready ---
Date: Friday, 2026-05-29 09:46 AM
Health: COMPOUNDING (K=456 | σ=0.95 | ρ=0.70)
Project: payments-api — last session: added idempotency keys; open Q: retry budget
Recalled: 5 notes (retrievalId: 20260529094636)
```

`/boot` anchored on the project's memory file, ran a health pulse, and pulled the five most relevant notes via `hive_retrieve`. You now start at "week 1," not "week 0."

```text
> The retry logic keeps double-charging. Help me fix it.
```

The agent already has the idempotency context from boot. It reads the relevant notes (`hive_read`), proposes a fix, and as decisions get made it persists them — a new resource note on the retry-budget trade-off, an update to the project memory.

```text
> /wrap
--- Session wrapped ---
Retro: captured 1 learning (retry budgets must be idempotency-key-scoped)
Feedback: 5 events recorded (3 helpful, 2 unused)
Handoff: appended to memory/projects/payments-api.md
Commit: pushed a1b2c3d
```

`/wrap` recorded which of the booted notes were actually *cited* during the work (`hive_feedback`) — the reinforcement signal that will re-rank retrieval next time — then captured the learning, updated project memory, and committed.

## 2. Retrieval that finds concepts, not keywords

```text
> /recall how do we handle backpressure in the ingest path?
```

`hive_retrieve` scores every note two ways — keyword composite *and* dense-vector similarity — then re-ranks by learned utility. A note titled "Token-bucket rate limiting for the upload queue" surfaces even though it never says "backpressure," because the dense vector recognizes the concept and the note has earned high utility in past sessions.

## 3. Measuring whether the system is healthy

```text
> /health
Health: COMPOUNDING | K=456 | σ=0.95 | ρ=0.70 | σ·ρ=0.66 vs δ/100=0.004 | dK/dt=+201/wk

> /sigma-rho
true σ=0.38  true ρ=0.53   (from 112 recorded feedback events, 197 scored notes)
```

`hive_health` reports the proxy metrics from the manifest; `hive_sigma_rho` computes the *measured* coverage/precision from accumulated `hive_feedback` events. Both confirm the base is above escape velocity — compounding, not decaying.

## 4. Closing the learning loop

```text
> /evolve
```

`evolve` scans where learnings were captured (`memory/feedback_*.md`, retros) and checks whether each has actually propagated into an operational surface — a rule, a skill, or a hook. It proposes specific patches for the ones that haven't, so a lesson learned once changes how the agent behaves from then on, instead of decaying in a memory file.

## 5. Keeping the graph healthy

```text
> /weekly-review        # "state of the hive" — what's compounding, what's decaying
> /prune                # archive stale notes, clean completed items
> /link-repair          # fix broken wikilinks, link orphans to MOCs
```

These maintenance skills keep **σ** high (everything reachable) and **δ** low (nothing rotting unlinked) — the two terms that decide whether the system stays above escape velocity.

---

*The σ/ρ/δ compounding model used throughout these examples is adapted from [AgentOps · The Science](https://boshu2.github.io/agentops/the-science/) (boshu2, Apache-2.0). See [CREDITS.md](CREDITS.md).*
