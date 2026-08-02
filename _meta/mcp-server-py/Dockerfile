# hivemind MCP server — container image.
#
# Build from THIS directory (_meta/mcp-server-py), which is the Python project
# root; the hive itself is mounted at runtime, never baked in:
#
#   docker build -t hivemind:latest .
#   docker build -t hivemind:embeddings --target runtime-embeddings .
#
# Run as an MCP stdio server (this is how .mcp.json would invoke it):
#
#   docker run -i --rm \
#     --user "$(id -u):$(id -g)" \
#     -v /path/to/hive:/hive \
#     hivemind:latest
#
# Debian slim, not Alpine: the embeddings extra pulls onnxruntime and numpy,
# which publish manylinux wheels and no musl wheels. Alpine would force both to
# build from source.

ARG PYTHON_VERSION=3.12

# ─────────────────────────────────────────────────────────────────────────
# Stage 1 — resolve dependencies from the committed uv.lock
# ─────────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /src

# Dependency layer first — editing src/ must not re-resolve the environment.
# --frozen fails loudly if uv.lock and pyproject.toml have drifted, which is
# the whole reason this image is reproducible.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
# --no-editable matters: the default editable install records /src/src in the
# venv, and that path does not exist in the runtime stage the venv is copied
# into. A non-editable install puts the package inside the venv itself.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ─────────────────────────────────────────────────────────────────────────
# Stage 2 — base deps only (~200 MB)
# ─────────────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

COPY --from=builder /src/.venv /app/.venv
COPY scripts/stdio-smoke.py /app/scripts/stdio-smoke.py

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# HIVE_PATH: the hive is a bind mount. Without this the server falls back to
#   _detect_hive_root() and resolves to a path that does not exist in here.
# OBSIDIAN_FALLBACK_MODE: filesystem is the source of truth in a container —
#   the Obsidian REST plugin listens on the host's 127.0.0.1, not this one's.
# HIVEMIND_EMBEDDINGS_BACKEND: with no weights mounted, `auto` degrades to the
#   dependency-free hashing embedding; hive_status reports which one is live.
ENV HIVE_PATH=/hive \
    OBSIDIAN_FALLBACK_MODE=fs_only \
    HIVEMIND_EMBEDDINGS_BACKEND=auto

WORKDIR /app

# Non-root. Bind-mounted hives keep host ownership when you pass
# `--user "$(id -u):$(id -g)"`, which is the recommended invocation.
RUN useradd --create-home --uid 1000 hive && chown -R hive:hive /app
USER hive

VOLUME ["/hive"]

# stdio transport: no port, no HEALTHCHECK. `docker run -i` is required —
# without -i the server sees immediate stdin EOF and shuts down.
ENTRYPOINT ["python", "-m", "hivemind"]

# ─────────────────────────────────────────────────────────────────────────
# Stage 3 — ONNX dense-retrieval backend (~600 MB)
# ─────────────────────────────────────────────────────────────────────────
FROM builder AS builder-embeddings
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra embeddings

FROM runtime AS runtime-embeddings
USER root
COPY --from=builder-embeddings /src/.venv /app/.venv
RUN chown -R hive:hive /app/.venv
USER hive

# Model weights are deliberately NOT baked in: scripts/fetch-embedding-model.py
# provisions them and they are never committed, so baking them would change
# what this image redistributes. Mount them instead:
#   -v $PWD/models/all-MiniLM-L6-v2:/models/all-MiniLM-L6-v2:ro
ENV HIVEMIND_EMBEDDINGS_MODEL_DIR=/models/all-MiniLM-L6-v2

ENTRYPOINT ["python", "-m", "hivemind"]
