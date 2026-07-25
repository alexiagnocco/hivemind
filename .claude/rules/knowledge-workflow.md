# Knowledge Compounding Workflow

## Core Principle

Every development session must increase the hive's knowledge stock `K` and maintain escape velocity: `sigma x rho > delta/100` — where **sigma** is retrieval coverage (how much of what you know you actually surface), **rho** is retrieval precision (how useful what you surface is), and **delta** is the decay rate (how fast unused knowledge goes stale). When `sigma·rho` exceeds `delta/100`, the knowledge base compounds faster than it decays. In practice this means: **retrieve before creating, persist during work, extract learnings after.** *(This model is adapted from [AgentOps · The Science](https://boshu2.github.io/agentops/the-science/); see CREDITS.md.)*

## Session Lifecycle (MANDATORY for all dev work)

### Phase 1: Context Load (Increase sigma — retrieval coverage)

Before writing any code or making decisions:

1. **Search the hive** for prior art — use `hive_search` for related decisions, patterns, past issues
2. **Load project memory** — check `memory/projects/<project>.md` for accumulated context
3. **Check relevant ADRs** — search `10-projects/` for architectural decisions that constrain this work
4. **Stay at 40% context** — load only what's relevant now; JIT-load the rest as needed

> Never start from zero. The hive exists to prevent every session from being Week 0.

### Phase 2: Active Development (Increase I(t) and rho)

During development:

1. **Persist decisions immediately** — design rationale, trade-offs, rejected alternatives go in the hive as they happen
2. **Link to prior knowledge** — every new note must reference what it builds on via [[wikilinks]]
3. **Use validation gates** — tests, reviews, linting are the ratchet pawl; don't skip them
4. **Update project memory** — append significant findings to `memory/projects/<project>.md`
5. **Capture blockers and workarounds** — these are high-value learnings that prevent future decay

### Phase 3: Knowledge Extraction (Prevent delta erosion)

Before ending a session with development work:

1. **Extract learnings** — any reusable pattern, gotcha, or insight gets its own note or gets appended to an existing one
2. **Update project memory** — `memory/projects/<project>.md` with outcomes, decisions, and open questions
3. **File new resources** — technical references go to `30-resources/<domain>/`, not left in chat
4. **Link to MOCs** — ensure new notes are reachable from the knowledge graph

### Phase 4: Scale Management (Control phi)

Periodically (not every session):

1. **Archive completed work** — move done projects to `40-archive/`
2. **Prune stale notes** — flag notes that haven't been retrieved or cited
3. **Update MOCs** — keep maps of content current so sigma stays high

## Anti-Patterns (NEVER do these)

- **Session amnesia** — Starting work without checking what the hive already knows
- **Chat-only knowledge** — Producing useful output that stays only in the conversation
- **Context stuffing** — Loading everything "just in case" (kills the 40% rule)
- **Skip the ratchet** — Bypassing validation gates to move faster (you lose the one-way progress guarantee)
- **Orphan notes** — Creating notes with no inbound links (invisible = decaying)

## How to Decide Where Knowledge Goes

| Knowledge Type | Destination | Why |
|---|---|---|
| Reusable pattern / technique | `30-resources/<domain>/` | High sigma — easy to find and retrieve |
| Project-specific decision | `memory/projects/<project>.md` | Contextual — compounds within project |
| Cross-domain insight | `30-resources/synthesis/` | Highest rho — connects disparate knowledge |
| Bug fix / workaround | `30-resources/<domain>/` or project note | Prevents re-investigation (reduces delta) |
| Meeting outcome / action item | `00-inbox/` for triage | Enters the flow pipeline |
