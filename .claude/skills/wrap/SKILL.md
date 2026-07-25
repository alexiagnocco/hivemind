---
name: wrap
description: "Graceful session shutdown: retro, feedback, handoff, commit, exit. Run this instead of just closing the window. Triggers: 'wrap', 'wrap up', 'end session', 'I'm done', 'closing out', 'session end', 'done for today'."
---

# /wrap — Graceful Session End

Run the full session-end lifecycle in one command, then exit. This replaces manually running `/retro`, `/feedback`, `/handoff` separately.

## Usage

`/wrap` -- full workflow (all phases)
`/wrap --quick` -- skip Phase 1 (retro), run everything else
`/wrap --light` -- minimal: handoff + commit + exit only

## Phases

Execute each phase in order. If a phase has nothing to do (e.g., no learnings to capture, no changes to commit), skip it and move to the next. Do NOT ask for confirmation between phases — just execute.

**Mode summary:**

| Flag | Phases run |
|------|-----------|
| (none) | 1 → 2 → 3 → 3.5 → 4 → 4.5 → 5 → 6 |
| `--quick` | 2 → 3 → 3.5 → 4 → 4.5 → 5 → 6 |
| `--light` | 4 → 5 → 6 |

Use `--light` for sessions under ~10 turns where there's nothing meaningful to retrospect and no hive notes were retrieved. The handoff (Phase 4) always runs because session continuity is non-negotiable.

### Phase 1: Retro (skip with `--quick` or `--light`)

Check if the session produced learnings worth capturing:
- Were there non-obvious patterns, gotchas, or workarounds discovered?
- Were there decisions with rationale that should be preserved?
- Were there surprises or failures that teach something?

If yes: persist each learning to the hive using the `/retro` skill's logic (search before creating, append when possible, create `30-resources/<domain>/` notes with frontmatter and links).

If no: skip silently. Not every session produces novel learnings.

### Phase 2: Feedback (skip with `--light`)

Run `/feedback --session` logic:
1. Check the session activity log for notes retrieved via `hive_retrieve` or `hive_search` this session.
2. For each retrieved note, determine if it was subsequently cited (referenced in created/edited files) or ignored.
3. Call `hive_feedback` for each batch: cited = helpful, ignored = not helpful.
4. Report count: "Recorded N feedback events."

If no notes were retrieved this session, skip silently.

### Phase 3: Session Check (skip with `--light`)

Run `hive_session_check` to validate knowledge persistence:
- Were new notes created with proper frontmatter?
- Were orphan notes left without inbound links?
- Was project memory updated?

Report any gaps but do NOT block on them — just note them for awareness.

### Phase 3.5: Prune Pulse (read-only, skip with `--light`)

Call the `hive_prune_dryrun` MCP tool to get candidate counts by category. Do NOT execute any moves, do NOT prompt for decisions, do NOT list every candidate. The goal is awareness, not action.

Report a single line:

```text
Prune pulse: N candidates (S stale, C completed, E empty, I inbox, M meta) — run /prune to triage
```

If N is 0, report "Prune pulse: clean" and move on. If `hive_prune_dryrun` errors or hivemind is unavailable, skip silently — wrap should never fail because of a read-only check.

### Phase 4: Handoff

Run `/handoff` logic:
1. Review session: files changed, decisions made, open questions.
2. Determine project from `pwd` (or hive context).
3. Append session handoff to `memory/projects/<project>.md` with: What Was Done, Decisions Made, In Progress, Open Questions, Next Session Start.
4. Update `updated:` field.

### Phase 4.5: CLAUDE.md Integrity Audit (skip with `--light`)

Validate the current project's CLAUDE.md against the actual filesystem and project state. This is a full cross-reference — not limited to what this session changed. Fix inaccuracies even if they were left behind by prior sessions.

#### Scope

- **Primary:** `CLAUDE.md` in the current working directory (`pwd`).
- **Secondary:** `CLAUDE.md` in any additional working directories touched this session.
- **Skip:** global `CLAUDE.md` files and the hive's own `CLAUDE.md` — these are managed separately.

If no `CLAUDE.md` exists in scope, skip silently.

#### Step 1 — Read and parse

Read the CLAUDE.md in full. Identify every verifiable claim: file paths, module/tool/test counts, directory structures, command syntax, architecture tables listing named components.

#### Step 2 — Cross-reference against reality

For each verifiable claim, check the filesystem or project state. Only flag claims you can verify with high confidence — leave ambiguous claims alone.

| Claim type | Verification method |
|---|---|
| File/module/tool counts ("8 modules", "19 tools") | `find`/`ls` the actual directory, compare count |
| Named files or paths ("src/orchestrator.py") | Check file exists at stated path |
| Directory structures ("11 packages, max depth 2") | Verify actual structure |
| Command syntax ("uv run pytest", "npm run dev") | Check against `pyproject.toml`, `package.json`, or actual scripts |
| Architecture descriptions (tables, module lists) | Verify named modules/files/directories exist |
| Baked-in metrics, scan outputs, or analysis results | Flag per the CLAUDE.md content rule: data comes from tools at analysis time, not static docs |

#### Step 3 — Apply fixes

- **0 discrepancies:** report "CLAUDE.md: current" and move on.
- **1–3 surgical fixes:** apply silently with the Edit tool. Report what changed in the Phase 6 summary.
- **4+ fixes:** show a brief diff preview in output (no confirmation gate — this is visibility, not a decision point), then apply all fixes.

#### Error resilience

If any filesystem check fails or an Edit call errors, log the failure in the Phase 6 summary and continue. `/wrap` must never fail because of CLAUDE.md validation.

#### What this phase does NOT do

- Add new sections or missing content — that's a separate doc-improvement pass.
- Restructure, reformat, or improve prose.
- Apply quality scoring or grades.
- Touch global or hive CLAUDE.md files.

### Phase 5: Commit

1. `git status` — if no changes, skip.
2. Stage all relevant files (by name, not `-A`).
3. Commit with a descriptive message + co-author line.
4. `git push origin HEAD`.

**Hive rebase safety:** if the hive remote has diverged and `git pull --rebase` is needed, never use `git stash -u`. The PreToolUse `pre-bash-hive-stash-guard.sh` hook hard-blocks `git stash drop` inside the hive; if you hit it, commit WIP before the pull instead of stashing.

### Phase 6: Exit

After all phases complete, print a final summary:

```text
--- Session wrapped ---
Retro: {captured N learnings | skipped}
Feedback: {N events recorded | skipped}
Session check: {COMPLETE | PARTIAL — N gaps}
Prune pulse: {clean | N candidates — run /prune to triage}
Handoff: {appended to memory/projects/<project>.md | skipped}
CLAUDE.md: {current | fixed N items: <brief list> | skipped — no file}
Commit: {committed + pushed <hash> | nothing to commit}
```

Then tell the user the session is complete and they can close the window or start a new task.

## Rules

- **Never ask for confirmation** between phases. The whole point is one-command shutdown.
- **Never skip handoff** — it's the most important phase for session continuity.
- **Never force push** — if push fails, report the error in the summary.
- **If the hive has no changes and no learnings**, the summary should reflect that honestly: "Clean session — nothing to persist."
- **Keep each phase concise** — this is a shutdown sequence, not a deep analysis. Retro captures should be quick notes, not full retrospectives.
- **Always end with the summary block** — it's the user's confirmation that everything ran.
