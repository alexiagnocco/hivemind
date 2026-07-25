# Eval Design

Deep-dive reference for the `ai-engineer` skill. Read this when building an eval harness, writing graders, or someone claims a change "seems better." RAG-specific retrieval metrics live in `rag-patterns.md` §5.

## 1. Eval-set curation

- **Source from reality**: production logs, bug reports, and support escalations first; synthetic cases only to fill coverage gaps. A synthetic-only eval set measures your imagination, not your system.
- **Size**: 10–30 cases to start iterating; 50–150 for release confidence. Small-and-real beats large-and-fake.
- **Coverage matrix**: rows = capability areas (e.g. lookup, multi-hop, refusal-appropriate, stale-vs-current), columns = difficulty (easy / hard / adversarial). One glance shows the holes.
- **Every production failure becomes a case**: minimal repro of input + expected behavior, added the day it's found. This is the compounding loop that makes the system improve instead of oscillate.
- **Version the set**: eval cases live in the repo (`evals/evals.json` or similar), reviewed like code. Scores are only comparable across runs on the same set version — record `set_version` with every result.
- **Hold-out discipline**: if you iterate prompts against the eval set, reserve 30–40% as a held-out split you check rarely. Otherwise you overfit the prompt to the test.

## 2. Code graders (use first, always)

Deterministic, free, no drift. Cover more than people expect:

```python
# Common assertion types — each returns (passed: bool, evidence: str)

def assert_contains(out, needle):            # key fact present
    return needle.lower() in out.lower(), f"looked for {needle!r}"

def assert_valid_schema(out, model):         # structured output parses
    try:
        model.model_validate_json(out); return True, "schema ok"
    except ValidationError as e:
        return False, str(e)[:200]

def assert_numeric_close(out, expected, tol=0.01):   # extracted number within tolerance
    got = extract_number(out)
    return abs(got - expected) <= tol, f"got {got}, expected {expected}"

def assert_cites_source(out, allowed_ids):   # every citation resolves to a real, retrieved doc
    cited = extract_citation_ids(out)
    bad = [c for c in cited if c not in allowed_ids]
    return not bad, f"unresolvable citations: {bad}" if bad else "citations ok"

def assert_refuses(out):                     # for cases where refusal IS the right answer
    return matches_refusal_pattern(out), "expected a refusal"
```

Also cheap to assert in code: latency ceiling, token ceiling, tool-call count, no-secrets-in-output.

## 3. LLM-as-judge (for what code can't measure)

Use for groundedness, tone, helpfulness, comparison of free-form answers.

- **Written rubric, always.** A judge without a rubric is a vibe with an API bill:

```
You are grading an answer for GROUNDEDNESS against provided source chunks.
Score 1–5:
5 = every claim supported by the chunks, correctly cited
4 = all claims supported; minor citation sloppiness
3 = mostly supported; one unsupported claim
2 = multiple unsupported claims
1 = answer contradicts the chunks or invents sources
Return JSON: {"score": n, "unsupported_claims": [...], "reasoning": "..."}
```

- **Judge ≠ generator**: different prompt at minimum; different model ideally. A generator's own prompt grading its output inherits its blind spots (the "self-grading" anti-pattern).
- **Calibrate before trusting**: have a human label 20–30 outputs, measure judge agreement. Below ~80% agreement, fix the rubric before using the judge in decisions.
- **Pairwise beats absolute for comparisons**: "which of A/B is better and why" is more reliable than independent 1–5 scores; randomize A/B order to kill position bias.
- **Judges drift**: pin the judge model version; re-calibrate when it changes.

## 4. Reporting discipline

- **No baseline, no claim.** Every reported result is `metric: baseline → after (Δ)` on a named eval-set version. This is the agent's output-contract rule, enforced.
- **Slice before celebrating**: aggregate score up 4 points can hide a regression in one capability row of the coverage matrix. Report per-slice.
- **Track the trend**: append every run to a results log (`run_id, date, change_desc, set_version, metrics…`). Three data points make a trend; one makes an anecdote.
- **Run-to-run variance**: LLM outputs vary. For metrics near a decision threshold, run 3× and report mean ± spread before acting.
- **Cost and latency are metrics too**: a +2-point quality win that doubles latency is a decision, not an obvious win — surface both.

## 5. Minimal harness shape

No framework needed to start — a runner script is enough:

```
evals/
├── evals.json          # cases: {id, prompt, files, assertions[]}
├── run_evals.py        # runs each case against the target, applies graders
└── results/
    └── 2026-07-10_rerank-added.json   # one file per run, named by change
```

Graduate to a real eval framework when you need parallel runs, dashboards, or team-shared history — not before.
