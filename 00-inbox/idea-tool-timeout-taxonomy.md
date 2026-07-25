---
created: 2026-07-22
updated: 2026-07-22
tags:
  - ai
status: draft
type: note
domain: work
seed: demo
---

# Idea — Tool Timeout Taxonomy

Raw capture, needs shaping.

Timeouts are getting lumped into one bucket and they're at least three different things:

- **Transport timeout** — never reached the backend. Retry freely, it's pure environment.
- **Execution timeout** — backend got it, work started, clock ran out. Retrying might duplicate work; this is where idempotency actually gets tested. Is the work still running server-side after we gave up? Sometimes! That's the nasty case — "slow but succeeding" cancelled at 99%.
- **Queue timeout** — backend accepted, never started. Retrying re-queues at the back; backoff makes it *worse* under load, want to fail over or shed instead.

Current loop treats all three as "environment error, backoff, retry" which is right for #1, half-right for #2, actively wrong for #3.

Maybe extend the taxonomy in [[error-taxonomy-for-agent-loops]] with a timeout sub-class? Needs: how does the caller even *distinguish* them — needs backend cooperation (accepted-at / started-at timestamps in the error envelope?). Sketch that envelope before proposing anything.
