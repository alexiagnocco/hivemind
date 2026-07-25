# Retrieval Order

How Claude traverses the hive to gather context when a user prompts.

## Default Algorithm (apply unless overridden by skill or explicit user direction)

```
1. CLASSIFY the prompt (no tool calls)
   - Project? (cwd basename, explicit name in prompt)
   - Domain? (backend, data, infra, testing, retrieval, meta, ai)
   - Specific query vs. exploratory ("landscape of X")?
   - Decision-shaped? (constrained by ADRs)

2. ANCHOR (zero or one read)
   - If project inferrable -> hive_read memory/projects/<project>.md
   - Else skip — do not read speculatively

3. RETRIEVE (one MCP call)
   - hive_retrieve(query, optional domain filter, max=5-10)
   - Capture retrievalId for end-of-session hive_feedback

4. EXPAND (one MCP call, if warranted)
   - hive_related on the top 1-2 retrieve hits
   - Merge novel neighbors, dedupe

5. READ SELECTIVELY (0-3 reads)
   - Only the 2-3 notes whose summary in step 3-4 proves insufficient
   - Prefer frontmatter + first section over full reads

6. ESCALATE only if needed
   - hive_search for keyword filters the retriever missed
   - hive_recent for activity-based questions
   - 50-maps/MOC-* if step 4 returns thin results AND prompt is exploratory

7. NEVER as a default
   - hive_manifest for per-query context (bulk analysis only)
   - MOC-first browsing (MOC connectivity is already a signal in hive_retrieve)
   - Reading whole directories
```

## Key Rules

- **Retrieve-first, not MOC-first.** `hive_retrieve` already incorporates MOC structure via the connectivity component of its composite score. MOCs are orienting maps for human browsing — Claude consumes their structure implicitly.
- **Anchor before retrieve.** Project memory is the highest signal-per-token read in the hive.
- **40% context rule applies at every step.** Stop reading once the next step has what it needs.
- **Capture `retrievalId`.** Every `hive_retrieve` call returns one — store it for `hive_feedback` at session end. This trains MemRL utility scores.
- **Thin results are diagnostic.** If retrieve + related returns nothing useful, the prompt is vague or the topic genuinely lacks coverage — say so rather than escalating blindly.

## Fallback Hierarchy (when hivemind MCP is unavailable)

1. Read `_meta/hive-manifest.json` to scope candidates by metadata
2. Use Grep against `30-resources/`, `memory/projects/`, `10-projects/`
3. Fall back to MOC browsing in `50-maps/` for landscape view
4. Notify the user that MemRL utility weighting is not active

## When MOC-first IS Correct

- Prompt is explicitly exploratory: "what do I know about X domain?"
- User is browsing for ideas, not solving a specific problem
- Cross-domain skills like `/connect` or `/weekly-review` (already coded that way)
- hivemind MCP is unavailable

## Reasoning

The ordering minimizes tokens-to-answer: anchor on the single highest-signal
note (project memory), let the scored retriever do the heavy lifting in one
call, expand only along the link graph, and read full notes only when summaries
prove insufficient. Each step is gated on the previous one returning too little.
