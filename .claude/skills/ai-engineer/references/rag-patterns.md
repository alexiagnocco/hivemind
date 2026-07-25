# RAG Patterns

Deep-dive reference for the `ai-engineer` skill. Read this when designing or debugging a retrieval pipeline. Companion eval detail lives in `eval-design.md`.

## 1. Chunking recipes

Pick the recipe that matches the corpus structure; tune sizes against retrieval evals, never by feel.

| Recipe | When | Notes |
|---|---|---|
| **Structure-aware** (split on headings/sections) | Docs, wikis, source code, anything with hierarchy | Default choice. Attach `doc_title`, `section_path`, `last_modified` to every chunk. |
| **Fixed-size + overlap** (e.g. 512 tok, 10–15% overlap) | Unstructured prose, transcripts | Overlap prevents answers straddling a boundary. Cheap fallback, not a first choice. |
| **Parent-child (small-to-big)** | Precise matching needed but generator wants context | Embed small chunks (100–300 tok) for retrieval; return the parent section (500–1500 tok) to the model. |
| **Semantic splitting** | Long undifferentiated text where topic shifts matter | Split where embedding similarity between adjacent windows drops. Costs an embedding pass at index time. |

Rules that hold regardless of recipe:

- Keep tables, code blocks, and lists intact — a half-table chunk is noise.
- Prepend a one-line contextual header to each chunk (`"[Doc: Batch Framework Guide > Restart/Recovery] ..."`). Cheap and measurably improves both retrieval and groundedness.
- Store chunk provenance (doc id, char offsets) so citations can link back.

## 2. Embedding model selection

- Decision axes: retrieval quality on *your* eval set, dimension count (storage + query cost), max input length, latency, and hosting constraints (local ONNX vs. API).
- Smaller local models (e.g. MiniLM-class, 384-dim) are often within a few points of large API models on in-domain corpora — measure before paying for the big one.
- **Version pinning**: an embedding model change invalidates the entire index. Record model name + version in index metadata and require a full reindex on change. Never mix embeddings from two models in one vector space.

## 3. Hybrid retrieval + reranking

The default high-performing stack:

```
query ──► BM25/keyword search ──► top 50 ─┐
      └─► dense vector search ──► top 50 ─┤─► RRF fusion ─► top ~25 ─► cross-encoder rerank ─► top 3–8 to the LLM
```

- **Fusion**: Reciprocal Rank Fusion (RRF) is robust and parameter-light — score each doc `Σ 1/(k + rank)` with k≈60 across both result lists. Start there before learned fusion.
- **Reranker**: a cross-encoder reranking a 20–50 candidate pool is usually the single biggest quality lever after chunking. It reads query+chunk together, which bi-encoders can't.
- **Metadata filters first**: if the query implies a filter (date range, product, doc type), apply it *before* semantic search — filtering after retrieval wastes the candidate pool.
- **k values**: retrieve generously (candidate pool 25–50), pass frugally (3–8 chunks to the generator). More context ≠ better answers; irrelevant chunks actively hurt groundedness.

## 4. Query handling

- **Query rewriting**: use a small/fast model to expand terse queries or resolve conversational references ("what about the second one?") into standalone queries before retrieval.
- **Filter extraction**: have the rewrite step also emit structured filters (dates, domains) rather than parsing them with regex.
- **HyDE** (hypothetical document embeddings): generate a hypothetical answer, embed *it*, search with that. Helps when queries and documents use different vocabulary; adds a generation call of latency — measure whether it earns its cost.

## 5. Retrieval evaluation setup

Evaluate retrieval **separately** from generation (see `eval-design.md` for grader mechanics).

1. Build a labeled set: 30–100 real queries, each mapped to the chunk/doc ids that contain the answer. Source from logs and known failure reports.
2. Core metrics:
   - **recall@k** — fraction of queries where a relevant chunk appears in top k (report k = candidate pool size AND k = chunks-passed-to-LLM).
   - **MRR** — how high the first relevant chunk ranks; sensitive to reranker quality.
3. Sketch:

```python
def recall_at_k(results: list[list[str]], relevant: list[set[str]], k: int) -> float:
    # results[i]: ranked chunk ids returned for query i
    # relevant[i]: set of chunk ids labeled correct for query i
    hits = sum(1 for r, rel in zip(results, relevant) if set(r[:k]) & rel)
    return hits / len(results)
```

4. Debug order when recall is low: inspect the actual retrieved chunks for 5–10 failing queries by hand first — the failure class (bad chunking vs. vocabulary mismatch vs. missing doc vs. stale doc ranked above current) determines the fix, and eyeballing finds it faster than metric archaeology.

## 6. Staleness and archival handling

Silent staleness is a top source of "the bot is wrong" reports. Choose one explicitly:

- **Hard filter**: exclude archived/superseded docs at query time (metadata flag). Right when old content is never useful.
- **Down-weight**: multiply retrieval score by a recency/status factor. Right when old content is occasionally the answer (e.g. legacy-system questions).
- **Label and let the model handle it**: pass status in the chunk header (`[ARCHIVED 2024]`) and instruct the generator to prefer current sources and say when it's citing archived material. Right for mixed corpora — costs prompt space.
- **Supersedence chains**: when a doc replaces another, store the link and redirect retrieval hits on the old doc to the new one.

Whichever you choose, add eval queries that specifically probe stale-vs-current conflicts.
