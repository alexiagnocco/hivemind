---
name: think-deep
description: "Extended reasoning for complex decisions — gathers hive context, reasons deeply, and persists the thinking chain"
---

# /think-deep — Extended Reasoning

Explicit deep reasoning for complex decisions. Gathers hive context, structures the decision space, evaluates options systematically, and persists the full reasoning chain as a permanent hive note. The thinking itself becomes knowledge.

## Usage

`/think-deep "<question>"` · `/think-deep --project <slug> "<question>"` · `/think-deep --compare "Option A vs Option B"`

## Recommended Mode

This skill explicitly benefits from extended thinking. If not already in plan mode, suggest:
> "Switch to plan mode (Shift+Tab) for deeper reasoning on this question."

## Behavior

1. **Check complexity** — if the question has a single clear answer with no meaningful tradeoffs, say so and suggest a lighter approach (`/recall` or a direct answer). Don't force deep analysis on simple questions.

2. **Gather context** — search the hive before reasoning (never start from scratch):
   - `hive_search` for notes mentioning the topic, decision keywords, and relevant domain terms
   - Read `memory/projects/<project>.md` if `--project` is specified or project is inferrable
   - Search `_meta/architecture-log.md` for related architectural decisions
   - Search `10-projects/` for ADRs that constrain the decision space
   - Check `30-resources/synthesis/` for prior cross-domain analysis on the topic
   - Check `30-resources/<domain>/` for established patterns and past decisions

3. **Frame the question** — structure the decision before analyzing it:
   - **Decision:** What specifically needs to be decided? (one sentence, precise)
   - **Context:** What does the hive already know about this? (cite notes with [[wikilinks]])
   - **Constraints:** What limits the options? (from ADRs, architecture decisions, project realities)
   - **Options:** What are the viable paths? (minimum 2, typically 3-4)
   - **Criteria:** What matters most? (derived from project goals and hive patterns)

4. **Reason deeply** — for each option, analyze across five dimensions:
   - **Pros:** What does this option enable? What value does it create?
   - **Cons:** What does this option cost, prevent, or make harder?
   - **Risks:** What could go wrong? Draw on past retros, anti-patterns, and pre-mortem thinking.
   - **Precedent:** Have we made similar decisions before? What happened? Cite hive notes.
   - **Second-order effects:** What does this decision unlock or block downstream? What future options does it preserve or foreclose?

5. **Synthesize recommendation** — converge on a clear position:
   - Recommendation with confidence level (high/medium/low)
   - The key factor that tips the decision — the single most important consideration
   - Reversibility conditions — what would change the recommendation
   - Specific next action if recommendation is accepted

6. **Persist to hive** — create a decision note based on the question type:
   - **Architectural decision:** `10-projects/<project>/ADR-NNN-<title>.md` with `type: decision`, `decision: accepted` (or `draft` if awaiting approval)
   - **Analytical question:** `30-resources/<domain>/<topic>-analysis.md` with `type: reference`
   - **Cross-domain synthesis:** `30-resources/synthesis/<topic>.md` with `type: note`, tag `#synthesis`
   - Include the full reasoning chain in the note body — don't summarize away the thinking
   - Frontmatter: `created`, `updated`, `tags`, `status: active`, `type`, `domain`, `parent: "[[relevant-MOC]]"`

7. **Update project memory** — if a project is identified, append the decision outcome and reasoning summary to `memory/projects/<project>.md`.

8. **Link into the graph** — ensure the new note has at least one inbound [[wikilink]] from a MOC, project note, or related resource. Add the link if it doesn't exist.

## Output Format

```
## Deep Analysis: <question>

### Context Loaded
- <N> hive notes consulted
- Key constraints: <list from ADRs and architecture decisions>
- Prior art: [[relevant-note-1]], [[relevant-note-2]]

### Decision Frame
**Decision:** <precise one-sentence statement>
**Criteria:** <what matters most, ranked>

### Options Evaluated

| Option | Pros | Cons | Risk | Confidence |
|--------|------|------|------|------------|
| A: ... | ...  | ...  | ...  | high/med/low |
| B: ... | ...  | ...  | ...  | high/med/low |
| C: ... | ...  | ...  | ...  | high/med/low |

### Deep Reasoning
<Full reasoning chain for each option — this is the deliverable.
Reference hive notes with [[wikilinks]]. Cite precedent.
Explore second-order effects. This section should be thorough.>

### Recommendation
**<Option X>** (confidence: high/medium/low)
<2-3 sentences explaining the key factor that tips the decision>

### What Would Change This
- If <condition>, reconsider <alternative>
- If <condition>, the risk profile shifts toward <option>

### Next Action
- <specific, actionable step to move forward>

### Recommended Next Steps
- <2-3 concrete follow-up actions>

Persisted to: [[<note-path>]]
```

## Confidence Levels

- **High (>80%):** Clear precedent in the hive, strong alignment with existing patterns, low uncertainty. One option is clearly better.
- **Medium (60-80%):** Some uncertainty remains, tradeoffs are real but one option edges ahead. More information could shift the balance.
- **Low (<60%):** Genuine tradeoffs, limited precedent, significant unknowns. The recommendation is a lean, not a conviction. Flag what information would increase confidence.

## --compare Mode

When invoked with `--compare "Option A vs Option B"`:
- Skip the option discovery step — the user has already scoped the comparison
- Still search hive for context on both options
- Give each option equal analytical depth (avoid anchoring on the first option listed)
- Explicitly state if there are options the user hasn't considered that hive context suggests

## Rules

- Always load hive context first — never reason from scratch (prevents session amnesia)
- Minimum 2 options analyzed — avoid confirmation bias even if one seems obvious
- Include at least one "what would change this" condition — decisions should be reversible
- The reasoning chain IS the deliverable — persist the full thinking, not a summary
- Reference prior decisions with [[wikilinks]] to build the decision graph over time
- If `--project` is given, scope context loading and note placement to that project
- End with Recommended Next Steps (mandatory per hive operating rules)
- Do not auto-execute the recommendation — present it for human decision
