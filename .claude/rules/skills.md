# Skills & Commands Reference

## Overview

Skills are slash commands that extend Claude Code with knowledge-management and
engineering capabilities. Each skill is a `SKILL.md` file in a skills directory
(`.claude/skills/<name>/`). Claude loads a skill when the user invokes `/<name>`
or when the task matches the skill's description.

## Session Lifecycle

| Command | Purpose |
|---|---|
| `/boot` | Session startup: date + health + context + recall + focus in one command |
| `/wrap` | Graceful session end: retro + feedback + handoff in one command |
| `/handoff` | Capture session context for continuity between sessions |

## Retrieval & Feedback

| Command | MCP tool | Purpose |
|---|---|---|
| `/recall <query>` | `hive_retrieve` + `hive_related` | Structured retrieval with relevance ranking. Use at session start. |
| `/retrieve <query>` | `hive_retrieve` | Hybrid keyword + dense-vector retrieval, re-ranked by MemRL utility |
| `/feedback <paths>` | `hive_feedback` | Record retrieval helpfulness — the MemRL training signal |
| `/sigma-rho` | `hive_sigma_rho` | Compute true sigma/rho from accumulated MemRL feedback |

## Knowledge Health & Maintenance

| Command | MCP tool | Purpose |
|---|---|---|
| `/health` | `hive_health` | Quick knowledge-health metrics (K, sigma, rho, delta, escape velocity) |
| `/health-check` | — | Diagnostic scan: orphans, broken links, missing frontmatter, stale content |
| `/prune` | `hive_prune_dryrun` | Archive stale notes, clean completed items, maintain scale |
| `/link-repair` | — | Fix broken wikilinks, link orphans to MOCs, repair escape-character bugs |

## Intelligence & Evolution

| Command | Purpose |
|---|---|
| `/evolve` | Propose structural improvements; propagate captured learnings into skills/rules |
| `/connect` | Find cross-domain connections and synthesis opportunities between notes |
| `/think-deep` | Extended reasoning for complex decisions — persists the thinking chain |
| `/weekly-review` | "State of the Hive" assessment — what's working, what's decaying, next actions |

## Capture

| Command | Purpose |
|---|---|
| `/new-note` | Create a note with proper frontmatter, naming, and linking |
| `/retro "insight"` | Capture learnings and retrospectives from development work |
| `/mine-sessions` | Find and extract knowledge from unmined Claude Code sessions |

## Engineering

| Command | Purpose |
|---|---|
| `/frame` | Design project scaffolds, directory hierarchies, and file-naming conventions |
| `/execute` | Pre-task discipline: think before coding, simplicity first, surgical changes |
| `/readme` | Generate a comprehensive, research-backed README.md for any project |
| `/ai-engineer` | LLM application playbook: RAG, agents, prompt/context engineering, tool use, structured outputs, evals. Pairs with the `ai-engineer` subagent for multi-file or research-heavy LLM work |

## Usage Rules

1. **Skills are interactive** — they may prompt for clarification before executing.
2. **Skills persist to the hive** — output lands in a hive file, not just chat.
3. **Skills use hivemind** — hivemind MCP tools are the primary data source for skills.
4. **Session protocol**: start with `/boot`, end with `/wrap`. Or use individual
   skills: `/recall`, `/retro`, `/feedback`, `/handoff`.

## Auto-Dispatch Heuristics

When the user's task matches a trigger, **invoke the specialized skill** rather
than free-reasoning:

- **Planning or implementing file/folder structure** (new scaffold, layout,
  reorganization, "where should this live?") → `/frame`
- **Any multi-step implementation, refactor, or feature build** → `/execute`
- **Anything LLM-powered** (RAG/retrieval quality, agent orchestration, prompt
  or context engineering, hallucination debugging, eval design, "which model
  should I use?") → `/ai-engineer`; delegate multi-file or research-heavy LLM
  work to the paired `ai-engineer` subagent

These skills exist to prevent the "reinvent ad-hoc" anti-pattern. If uncertain
whether a task qualifies, invoke them — they're idempotent and fast.

## Skill Architecture

Skills follow the `SKILL.md` directory pattern:

```
skills/
  skill-name/
    SKILL.md          # Main skill definition (frontmatter + instructions)
    references/       # Optional: supporting reference docs
    scripts/          # Optional: helper scripts
```

Keep `SKILL.md` to ~1,500–2,000 words; move deep reference material to
`references/` and reusable code to `scripts/`. The `description` frontmatter
field is the routing mechanism — make it specific and enumerate trigger phrases.
