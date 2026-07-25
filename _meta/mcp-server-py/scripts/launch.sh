#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"                 # _meta/mcp-server-py
REPO_ROOT="$(dirname "$(dirname "$PROJECT_DIR")")"     # the hive repo root

# .mcp.json does not expand ${VAR} — a literal string would ship — so this
# wrapper owns all path/env resolution. An explicit HIVE_PATH in the
# environment still wins; otherwise the hive is this repository.
export HIVE_PATH="${HIVE_PATH:-$REPO_ROOT}"

# Use fetched embedding weights when present (scripts/fetch-embedding-model.py
# provisions them; they are never committed). Without them the server's `auto`
# backend falls back to hashing and hive_status reports the active backend.
DEFAULT_MODEL_DIR="$PROJECT_DIR/models/all-MiniLM-L6-v2"
if [ -z "${HIVEMIND_EMBEDDINGS_MODEL_DIR:-}" ] && [ -f "$DEFAULT_MODEL_DIR/model.onnx" ]; then
    export HIVEMIND_EMBEDDINGS_MODEL_DIR="$DEFAULT_MODEL_DIR"
fi

# Filesystem is the default source of truth; the MemRL loop stays live without
# Obsidian REST. An explicit OBSIDIAN_FALLBACK_MODE still wins.
export OBSIDIAN_FALLBACK_MODE="${OBSIDIAN_FALLBACK_MODE:-fs_only}"

unset VIRTUAL_ENV

if [ -z "${OBSIDIAN_API_KEY:-}" ]; then
    OBSIDIAN_API_KEY="$(python3 -c "
import keyring
k = keyring.get_password('hivemind', 'obsidian-rest')
if k:
    print(k, end='')
" 2>/dev/null || true)"
fi

if [ -n "${OBSIDIAN_API_KEY:-}" ]; then
    export OBSIDIAN_API_KEY
fi

cd "$PROJECT_DIR"
exec uv run python -m hivemind
