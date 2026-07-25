# Subagent Patterns

## When to Use Subagents

- Parallel hive mining (3+ domains or project memories)
- Rename/refactor safety audits (3+ files changing)
- Cross-project pattern search (feature analogs)
- Pre-commit multi-dimensional validation
- Any task where independent reads can be parallelized

## Agent Type Selection

| Task Type | Agent Type | Why |
|-----------|-----------|-----|
| Read-only research | `Explore` | Fast, inherently safe (no Edit/Write), thoroughness levels |
| Read-only audit | `Explore` | Can't accidentally modify during validation |
| Pattern finding | `Explore` | Core purpose — codebase exploration |
| Needs Bash execution | `general-purpose` | Explore lacks Bash tool |
| LLM application work (RAG, agents, prompts, evals) | `ai-engineer` | Domain playbook preloaded; returns a structured decision record |
| Needs file writes | **Don't delegate** | Keep writes in main thread |

**Default to `Explore`** unless the task requires Bash or file modification.

**Exception — `ai-engineer`:** multi-file LLM implementation, eval-harness
builds, and retrieval-quality debugging delegate to the `ai-engineer` agent
(`.claude/agents/ai-engineer.md`), which inherits all tools and may write files.
Its paired skill (`.claude/skills/ai-engineer/`) defines when to delegate vs.
stay inline; its output contract (decision record + changes + eval results +
risks) keeps the main thread's context clean.

## Model Selection

**Default: `opus`** (Opus 4.6). Only downgrade to `sonnet` when the task is clearly mechanical.

| Task Complexity | Model | Examples |
|----------------|-------|---------|
| Complex reasoning, synthesis, architecture | `opus` (default) | Cross-project bridge, skill generation, deep analysis |
| Structured extraction, pattern matching | `sonnet` | Frontmatter validation, wikilink integrity checks, naming compliance |

**Rules:**
- When in doubt, use `opus` — quality matters more than speed for knowledge work
- Never use `haiku` for subagents — insufficient reasoning for hive tasks
- Parallel research agents: `opus` (they need to understand context and extract insights)
- Pre-commit validators: `sonnet` (mechanical checks with clear pass/fail criteria)
- Rename safety audits: `opus` (need judgment about what constitutes a stale reference)

## Background vs Foreground

| Pattern | Mode | When |
|---------|------|------|
| Research needed before next step | **Foreground** (default) | You can't proceed without the results |
| Independent generation (skill building, note creation) | **Background** | Results don't block current work |
| Validation before commit | **Foreground** | Must see results before acting |
| Multiple research threads, some blocking | **Mixed** | Foreground for critical path, background for nice-to-have |

## Worktree Isolation

Use `isolation: "worktree"` when an agent needs to experiment with file changes without touching the working tree:
- Parallel feature explorations ("try approach A vs approach B")
- Safe refactoring experiments
- Code generation that might need revision before merging

Worktrees auto-clean if the agent makes no changes. If changes are made, the path and branch are returned for review.

**Don't use worktrees for:** read-only research (Explore agents), validation checks, hive mining.

## When NOT to Use Subagents

- Single-file reads (use Read directly)
- Simple grep for a known symbol (use Grep directly)
- Tasks requiring file writes (keep in main thread)
- When the answer is likely in 1-2 files (faster to read directly)

## Thoroughness Levels (Explore Only)

- **"quick"** — basic search, known file patterns, <30 seconds
- **"medium"** — moderate exploration, multiple directories, ~1 minute
- **"very thorough"** — comprehensive analysis, multiple naming conventions, ~2-4 minutes

## Pattern: Parallel Research

When a task requires knowledge from 3+ hive domains simultaneously:

```
Explore Agent 1: Mine domain A (very thorough)
Explore Agent 2: Mine domain B (very thorough)
Explore Agent 3: Mine domain C (very thorough)
Main thread: Synthesize all findings → decide → persist
```

## Pattern: Rename Safety Audit

When renaming/moving/rebranding 3+ files, spawn an Explore agent to run the 7-point checklist:
1. Frontmatter `project:` slug references
2. `status:` field for archived files
3. Hive backups in `30-resources/` vs active skills
4. `.claude/rules/`, `.claude/skills/`, CLAUDE.md stale references
5. MOC tables with old names
6. Hook scripts and settings.json dispatch references
7. Manifest rebuild needed

## Pattern: Cross-Project Bridge

When starting implementation, spawn an Explore agent to read all `memory/projects/*.md` and search for:
- Similar problem patterns in other projects
- Reusable solutions already discovered
- Past decisions that constrain the current work

## Pattern: Pre-Commit Validation

Before commits touching hive notes, spawn parallel Explore agents:
- Agent 1: Frontmatter validation (required fields, dates, tag vocab)
- Agent 2: Wikilink integrity (no broken links, no new orphans)
- Agent 3: Naming convention compliance

## Agent Continuation (SendMessage)

Use `SendMessage` to continue a previously spawned agent instead of spawning a new one when:
- Agent returned initial findings but you need deeper detail on one specific item
- Agent's search was incomplete and needs refinement with additional paths or patterns
- You want to ask a follow-up question while the agent retains its full context

**Why:** Cheaper and more precise than a fresh agent. The continued agent remembers everything it already found — no re-reading, no context loss.

```
Step 1: Spawn Explore agent → mines project memories → reports 5 patterns
Step 2: SendMessage to same agent → "Expand on pattern #3, read the full note and extract implementation details"
Step 3: Agent responds with deep detail, still holding all prior context
```

**Don't use SendMessage when:** the follow-up is unrelated to what the agent already explored (spawn a new one instead).

## Pattern: Map-Reduce (Sequential Chaining)

When Agent B needs Agent A's findings:

```
Phase 1 (scatter): Spawn N parallel agents for broad research
Phase 2 (gather): Main thread receives all results, identifies key items
Phase 3 (focus): Spawn 1 agent (or SendMessage) for deep analysis on the key items only
```

This avoids the anti-pattern of giving a single agent too broad a scope. The main thread acts as the intelligent filter between phases.

**Example:**
- Phase 1: 3 Explore agents each mine a domain → return 15 relevant notes total
- Phase 2: Main thread identifies 4 notes that are directly actionable
- Phase 3: 1 Explore agent reads those 4 notes deeply + their link-graph neighbors

## Prompt Quality Guidelines

Agent prompts must include these elements (terse prompts produce shallow work):

1. **What you're trying to accomplish** — the goal, not just the task
2. **What you already know or ruled out** — prevents the agent from retreading ground
3. **Specific file paths or search patterns** — concrete starting points, not vague directions
4. **Why it matters** — enough context for the agent to make judgment calls
5. **Expected output format** — "report as a table", "under 200 words", "list of file paths with findings"
6. **Length constraint** — unbounded prompts get unbounded (and often shallow) results

**Bad prompt:** "Search the hive for patterns"
**Good prompt:** "In /home/user/hive/memory/projects/, read all 13 .md files and extract any mentions of credential management patterns. I'm looking for reusable approaches across projects. Report as a table: project | pattern | outcome. Under 300 words."

## Concurrency and Failure Handling

**Concurrency limits:**
- **Recommended max:** 4-6 parallel agents for research tasks
- **Hard signal to stop:** If >3 agents return thin or irrelevant results, the prompts are too vague — refine scope before spawning more
- Beyond 6, diminishing returns set in (main thread synthesis becomes the bottleneck)

**When an agent fails or returns poor results:**
1. **Don't retry blindly** — diagnose why (too broad? wrong files? ambiguous question?)
2. **SendMessage first** — refine the ask with the same agent (it has context)
3. **Fresh agent only if** the original scope was fundamentally wrong
4. **Never ignore poor results** — thin findings usually mean the search space was wrong, not that there's nothing to find

**When an agent times out:**
- Check if partial results were captured in the output file
- If the task was too large, split into 2-3 smaller agents with tighter scope
- Timeout usually means over-scoped, not slow execution

## Core Principles

1. **Explore for reads, main thread for writes** — enforces "agents draft, humans curate"
2. **Scope tightly** — specific file paths and search patterns, not open-ended questions
3. **Parallel for independent work; sequential for dependent work**
4. **Report back, don't act** — agents return findings; main thread decides
5. **Brief agents like a colleague** — include what you know, what you've ruled out, and why it matters
6. **Continue before respawning** — use SendMessage to refine, not a fresh agent
7. **Diagnose before retrying** — thin results mean bad scope, not bad luck
