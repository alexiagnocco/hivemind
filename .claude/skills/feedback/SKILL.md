---
description: "Record whether retrieved hive notes were helpful (MemRL feedback loop)"
---

# /feedback — Retrieval Feedback

Record which notes were actually useful after a `/recall` or `hive_retrieve`. This trains the MemRL utility scoring so future retrievals surface better results.

## Usage

`/feedback <paths> --helpful` · `/feedback <paths> --not-helpful` · `/feedback --session`

## Behavior

### Explicit mode (`/feedback <paths>`)

1. **Parse** — Accept comma-separated note paths and a helpful/not-helpful flag.
2. **Record** — Call `hive_feedback` with `paths` and `helpful` boolean.
3. **Confirm** — Report which notes were rated and current utility trend.

### Session mode (`/feedback --session`)

1. **Review** — Check session activity log for notes that were retrieved via `/recall` or `hive_retrieve` this session.
2. **Classify** — For each retrieved note, check if it was subsequently cited (referenced in created/edited files) or ignored.
3. **Record** — Call `hive_feedback` for each: cited = helpful, ignored = not helpful.
4. **Report** — Summary of feedback recorded.

## Why This Matters

MemRL utility scoring uses exponential moving average: `utility = (1-alpha) * utility + alpha * reward`. Notes rated helpful rise in future retrievals. Notes rated not-helpful sink. Without feedback, retrieval quality stagnates.

## MCP Tool

Primary: `hive_feedback`
Supporting: `hive_sigma_rho` (to show impact of accumulated feedback)
