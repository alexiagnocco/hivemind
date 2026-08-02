# hivemind

A [FastMCP](https://github.com/jlowin/fastmcp) MCP server that gives Claude Code
(and any MCP client) structured, persistent access to a local Markdown knowledge
vault. It works directly against the filesystem and can optionally drive the
Obsidian Local REST API for live read/write when Obsidian is running.

- **Stack:** Python 3.12, FastMCP, httpx, pydantic-settings, keyring.
- **Architecture:** REST-first (Obsidian Local REST API) with per-tool FS
  fallback via a `Dispatcher`. A `ConnectionMonitor` tracks REST health.
- **23 tools** spanning search/read, link-graph, knowledge-health (MemRL),
  checkpoints, and REST-only writes (PATCH, periodic notes, commands).

## Install

```bash
uv venv --python 3.12
uv sync --extra dev            # runtime + test/lint/type deps
```

The server is launched via `scripts/launch.sh` (it `unset`s `VIRTUAL_ENV`
before `uv run` to avoid the Claude Code runtime's `/usr` venv warning).

## Configuration

Settings load from environment variables or a `.env` file (see `config.py`).
The API key falls back to the OS keyring (`keyring.get_password("hivemind",
"obsidian-rest")`).

| Variable | Default | Purpose |
|---|---|---|
| `HIVE_PATH` | `~/vault` | Vault root |
| `OBSIDIAN_REST_URL` | `https://127.0.0.1:27124` | Local REST API base |
| `OBSIDIAN_API_KEY` | — | Bearer token (or via keyring) |
| `OBSIDIAN_FALLBACK_MODE` | `auto` | `auto` \| `rest_only` \| `fs_only` |
| `HIVEMIND_EMBEDDINGS_BACKEND` | `auto` | `auto` \| `onnx` \| `hashing` \| `none` |
| `HIVEMIND_EMBEDDINGS_MODEL_DIR` | — | Dir with `model.onnx` + `tokenizer.json` |
| `HIVEMIND_EMBEDDINGS_DIM` | `256` | Hashing-backend vector dimension |
| `HIVEMIND_DENSE_WEIGHT` | `1.0` | Weight of dense vs keyword in fusion |

## Tools

`hive_status`, `hive_search`, `hive_read`, `hive_recent`, `hive_related`,
`hive_manifest`, `hive_rebuild`, `hive_document_map`, `hive_tags`,
`hive_active`, `hive_retrieve`, `hive_health`, `hive_context`,
`hive_session_check`, `hive_feedback`, `hive_sigma_rho`, `hive_prune_dryrun`,
`hive_unmined_sessions`, `hive_checkpoint`, `hive_patch`, `hive_periodic`,
`hive_command`, `hive_open`.

## Hybrid retrieval (`hive_retrieve`)

`hive_retrieve` performs **hybrid composite + dense-vector retrieval with
two-stage re-ranking**:

1. **Fusion / candidate generation.** Every eligible note is scored by both the
   keyword composite (`match·3 + freshness·2 + connectivity·1`) and dense cosine
   similarity, then ranked by `zNorm(keyword) + W_DENSE·zNorm(dense)`. Because
   candidacy no longer requires a keyword match, a conceptually relevant note
   with no shared keywords still surfaces.
2. **Re-ranking.** The top pool is re-ranked with the learned MemRL utility
   signal: `+ LAMBDA_UTILITY·zNorm(utility)`.

The response includes `"mode": "hybrid" | "keyword"`. With no embedding backend
configured (or an empty query) it falls back to the original keyword-only path.

### Embedding backends

| Backend | Dependencies | Notes |
|---|---|---|
| Hashing (default fallback) | none | Deterministic SHA-1 feature hashing. Always available. **Lexical, not semantic.** |
| ONNX | `embeddings` extra | Real sentence-transformer (e.g. all-MiniLM-L6-v2) via onnxruntime. **Semantic.** |

Per-note vectors are cached incrementally in `_meta/hive-embeddings.json`
(gitignored); only changed notes re-embed.

### Enabling the semantic (ONNX) backend

```bash
uv sync --extra embeddings
uv run --extra embeddings python scripts/fetch-embedding-model.py   # downloads MiniLM ONNX
export HIVEMIND_EMBEDDINGS_BACKEND=onnx
export HIVEMIND_EMBEDDINGS_MODEL_DIR=$PWD/models/all-MiniLM-L6-v2
# restart the server
```

Model weights are provisioned on demand and never committed.

## Docker

A container image is the zero-install path for anyone who doesn't want uv on
their machine. The hive is mounted at runtime and never baked into the image.

```bash
docker build -t hivemind:latest .                                  # base (~200 MB)
docker build -t hivemind:embeddings --target runtime-embeddings .  # + ONNX (~600 MB)
```

Wire it into `.mcp.json`:

```json
{
  "mcpServers": {
    "hivemind": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/absolute/path/to/hive:/hive",
        "ghcr.io/<owner>/hivemind:latest"
      ]
    }
  }
}
```

- **`-i` is mandatory.** An MCP stdio server sees immediate stdin EOF without it
  and shuts down before the handshake completes.
- **Pass `--user "$(id -u):$(id -g)"`** so notes the server writes keep your
  ownership rather than the container's uid 1000.
- **Model weights are not in the image.** Run `python scripts/fetch-embedding-model.py`
  and mount the result at `/models/all-MiniLM-L6-v2`; without it the `auto`
  backend degrades to the hashing embedding and `hive_status` says so.
- **`OBSIDIAN_FALLBACK_MODE=fs_only` is the default here.** The Obsidian REST
  plugin listens on the *host's* 127.0.0.1, which is not the container's.

> **Keyring does not work in a container.** `scripts/launch.sh` falls back to
> `keyring.get_password("hivemind", "obsidian-rest")` when `OBSIDIAN_API_KEY` is
> unset. There is no D-Bus secret service in the image, so that lookup yields
> nothing and the server starts with an empty key. Pass `OBSIDIAN_API_KEY`
> explicitly (`-e OBSIDIAN_API_KEY=…`) if you need REST mode.

Smoke-test a built image:

```bash
docker run -i --rm -e HIVE_PATH=/hive -e HIVEMIND_SMOKE_CMD='python -m hivemind' \
  -v "$PWD/../..:/hive:ro" --entrypoint python \
  hivemind:latest /app/scripts/stdio-smoke.py --handshake-only
```

`docker-compose.yml` wraps the build and that smoke run; `.github/workflows/publish-image.yml`
builds, smoke-tests, and pushes to GHCR on a `v*` tag.

## Development

```bash
uv run ruff check src tests     # lint
uv run mypy                     # strict type check
uv run pytest -q                # tests
```

`scripts/stdio-smoke.py` boots the server through `launch.sh` by default; set
`HIVEMIND_SMOKE_CMD` to point it at any other server command (the container image
has no launcher).

Tests live in `tests/`. The ONNX backend test runs against a tiny committed
fixture (`tests/fixtures/tiny-onnx/`) and skips when the `embeddings` extra is
not installed.
