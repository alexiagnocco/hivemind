---
name: evolve
description: Propose structural improvements to the hive AND propagate captured learnings (memory/feedback, retros) into operational surfaces (skills, rules, CLAUDE.md, MCP tools, hooks). Use when the hive feels cluttered, when proactive architecture recommendations are wanted, or when lessons captured in memory/ haven't yet changed how Claude behaves.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(find *), Bash(wc *), Bash(sort *), Bash(python3 *), Bash(stat *)
---

# Hive Evolution

> **Recommended mode: Plan.** This is the most reasoning-intensive skill — pattern detection, drift analysis, and structural proposals all benefit from extended thinking. Switch with `Shift+Tab` if you're not in plan mode.

Analyze the hive's current state and propose structural improvements. This is the self-evolving core of the second brain.

## Step 1: Pattern Detection

Use `hive_manifest()` to load the full hive index. Analyze manifest metadata for structural signals — this replaces manual file scanning:

- **Cluster detection**: Find groups of 5+ notes sharing common tags or frequent cross-links that don't yet have a MOC. (Analyze manifest `tags` and `links` fields.)
- **Overgrown folders**: Folders with >20 direct children that should be subdivided. (Group manifest `path` by parent directory.)
- **Underused structure**: Folders with <3 notes that might be premature organization.
- **Tag sprawl**: Tags used only once (candidates for consolidation or removal). (Count tag frequency across manifest.)
- **Naming drift**: Files not following the naming conventions in CLAUDE.md. (Check manifest `title` / `path` patterns.)

## Step 2: Schema Evolution

Check if the frontmatter schema is serving the hive well:

- Are there fields being consistently left blank? (maybe remove or make optional)
- Are there patterns in content that suggest a new field is needed?
- Are tags being used consistently, or is there synonym drift? (e.g., `retrieval` vs `search` vs `ranking`)

## Step 3: Methodology Check

Evaluate whether the hybrid PARA + Zettelkasten + MOC approach is working:

- Are Projects actually getting completed and archived, or rotting in place?
- Are Areas being maintained, or are they just folders with notes dumped in them?
- Are MOCs being used for navigation, or are they stale indexes no one reads?
- Is the Zettelkasten principle (atomic, linked notes) being followed, or are notes monolithic?

## Step 4: Lessons Application Audit

The hive captures learnings in five substrates. This step checks whether those learnings are actually reflected in the operational surfaces that govern Claude's behavior — and proposes specific patches where they aren't. Without this loop, lessons decay in memory files without ever changing how Claude works.

### Sources (the learning substrate)

| Source | What's there | Signal |
|---|---|---|
| `memory/feedback_*.md` | Atomic "always do X when Y" memories (`type: feedback`) | Each file is a rule that should be reflected somewhere |
| `30-resources/ai-ml/retro-*.md` | Retrospectives with recommendations | Each retro should have its recommendations closed out |
| `_meta/open-questions.md` | Outstanding questions / unresolved tensions | Questions older than 30d need a decision or drop |
| `_meta/architecture-log.md` | Past proposals with accepted/rejected outcomes | Accepted proposals older than 14d with no follow-through are debt |

### Targets (the operational surfaces)

| Surface | Location | What lives there |
|---|---|---|
| Skills | `.claude/skills/` | `/recall`, `/handoff`, `/evolve`, etc. |
| Modular rules | `.claude/rules/*.md` | Architecture, frontmatter, retrieval-order, nudge-system, subagent patterns |
| Project instructions | `CLAUDE.md` | Top-level hive operating rules |
| MCP tool descriptions | hivemind server definition | Tool-use prompts that govern when to invoke what |
| Hooks | `.claude/hooks/` + `settings.json` | Automated behaviors (stop-session-hygiene, lint) |

### Audit procedure

For each source entry (prioritize newest first), determine:

1. **What behavior does this learning prescribe?** (e.g., "grep for feedback_*.md before enterprise commits")
2. **Where should that behavior live?** Pick ONE target surface — the most specific applicable one wins. Priority order:
   - Hook (if the behavior can be enforced mechanically at a trigger point) →
   - Rule file (if it's a durable, cross-skill convention) →
   - Specific skill SKILL.md (if it only applies when that skill is invoked) →
   - CLAUDE.md (only for hive-wide operating rules that don't fit elsewhere) →
   - MCP tool description (if it changes when a tool should be invoked)
3. **Is it already reflected there?** Grep the target for the relevant keywords/phrases.
4. **If not, draft a specific patch.** Include the target file path, the insertion point (which heading/section), and the exact text to add.

### Anti-patterns to avoid

- **Promoting one-off feedback to a rule too early.** If a pattern appears in only one `feedback_*.md` file, leave it there. Promote to a rule only when the same lesson surfaces 2+ times across feedback/retros.
- **Duplicating content across surfaces.** If a lesson is already in a rule file, don't also add it to three skills. Rules files are loaded automatically — skills should reference them, not copy them.
- **Skill bloat.** Don't append every learning to every skill. A skill should only absorb lessons that specifically apply when that skill is invoked.
- **Silent auto-apply.** Never edit operational surfaces without a proposal and approval, even when the patch feels trivial.

### Output

Append a "Lessons Application Audit" section to the evolution proposals:

```markdown
### Lessons Application Audit — YYYY-MM-DD

**Sources scanned**: N feedback memories, N retros, N open questions, N aged-accepted proposals
**Learnings already reflected**: N (no action needed)
**Learnings needing propagation**: N (proposals below)

**Propagation proposals**:
1. **[Target file]** — [learning summary] — [patch: insertion point + text]
   - Source: [memory/feedback_foo.md | retro-X.md]
   - Why this target: [rule > skill > CLAUDE.md reasoning]

**Elevation candidates** (patterns surfacing 2+ times — consider elevating memory → rule):
- [pattern] appears in [sources] → propose new rule or extend existing rule in `.claude/rules/`

**Aged-accepted debt** (proposals marked accepted >14d ago with no follow-through):
- [proposal date/title] → [current state vs. accepted action]
```

If every learning is already reflected, say so — this means the loop is closing cleanly.

## Step 5: Generate Proposals

For each recommended change, write a proposal with:

```markdown
### Proposal: [Short Title]

**Type**: [New MOC | Folder restructure | Schema change | Tag cleanup | Archive sweep | Rule update | Skill update | CLAUDE.md update | MCP tool update | Hook update | Lesson elevation]
**Impact**: [High | Medium | Low]
**Effort**: [Minutes | Hours]
**Source** (for lesson-propagation proposals): [memory/feedback file | retro file | accepted proposal]
**Rationale**: [Why this change, with evidence from the hive]
**Action**: [Specific steps to implement — for operational-surface patches, include the target file path, insertion point, and exact text to add]
```

## Step 6: Log and Present

- Append proposals to `_meta/architecture-log.md` with today's date and status `proposed`
- When the user accepts/rejects, update status to `accepted` or `rejected` with a brief reason
- Display the top 3 proposals in the terminal, ranked by impact

## Rules

- Never execute changes without approval
- Prefer small, incremental refactors over big-bang restructures
- Every proposal must cite specific evidence from the hive (file names, counts, patterns, or source memory/retro path for lesson propagation)
- If the hive is healthy and nothing needs changing, say so — don't invent busywork
- For lesson-propagation proposals: pick exactly ONE target surface (don't duplicate the same lesson across skills, rules, and CLAUDE.md)
- Require 2+ independent sources before promoting a pattern from `memory/feedback_*.md` to a rule in `.claude/rules/` — one-off feedback stays in memory
