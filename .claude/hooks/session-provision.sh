#!/usr/bin/env bash
# SessionStart: self-provision the engram platform so a fresh session — local
# clone or Claude Code on the web — boots green with zero manual setup.
#
#   1. uv sync (dev + embeddings extras; falls back to dev-only)
#   2. build the vault manifest (server-native builder, no extra deps)
#   3. best-effort fetch of embedding weights (hashing fallback otherwise)
#   4. stdio smoke test via scripts/stdio-smoke.py — an interactive client
#      that holds stdin open until responses land; stdio servers cancel
#      in-flight calls on stdin EOF, so a shell pipe is not equivalent
#
# Every failure prints one actionable line; the hook never blocks the session
# (always exits 0). Stdout lands in the session context as a status block.
set -u

INPUT="$(cat 2>/dev/null || true)"
SOURCE="$(printf '%s' "$INPUT" | jq -r '.source // "startup"' 2>/dev/null || echo startup)"
# Provision on fresh startups only — resume/clear reuse the provisioned container.
case "$SOURCE" in
  startup) ;;
  *) exit 0 ;;
esac

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SERVER_DIR="$ROOT/_meta/mcp-server-py"
MODEL_DIR="$SERVER_DIR/models/all-MiniLM-L6-v2"
unset VIRTUAL_ENV
export VAULT_PATH="${VAULT_PATH:-$ROOT}"

say() { printf 'engram provision: %s\n' "$1"; }

if ! command -v uv >/dev/null 2>&1; then
    say "SKIPPED — uv not found; install https://docs.astral.sh/uv/ then run: bash $ROOT/.claude/hooks/session-provision.sh"
    exit 0
fi

# 1. Dependencies
EMBEDDINGS_SYNCED=1
if (cd "$SERVER_DIR" && uv sync --extra dev --extra embeddings >/dev/null 2>&1); then
    DEPS="deps OK (dev+embeddings)"
elif (cd "$SERVER_DIR" && uv sync --extra dev >/dev/null 2>&1); then
    DEPS="deps OK (dev only; embeddings extra unavailable)"
    EMBEDDINGS_SYNCED=0
else
    say "FAILED at uv sync — run: cd $SERVER_DIR && uv sync --extra dev (check the network policy)"
    exit 0
fi

# 2. Vault manifest (retrieval is empty without it on a fresh clone)
if MANIFEST_OUT="$(cd "$SERVER_DIR" && uv run python -c "
import os
from pathlib import Path
from engram.manifest.builder import build_and_write_manifest
print(build_and_write_manifest(Path(os.environ['VAULT_PATH'])))
" 2>&1)"; then
    # First line reads: "Manifest built: N notes -> <path>"
    MANIFEST="$(printf '%s\n' "$MANIFEST_OUT" | head -1 | sed 's/ ->.*//')"
else
    say "manifest build FAILED: $(printf '%s\n' "$MANIFEST_OUT" | tail -1) — retry via the vault_rebuild MCP tool once the server is up"
    MANIFEST="manifest missing"
fi

# 3. Embedding weights (never committed; fetched on demand)
if [ -f "$MODEL_DIR/model.onnx" ]; then
    WEIGHTS="weights present"
elif [ "${ENGRAM_SKIP_WEIGHTS_FETCH:-0}" = "1" ]; then
    WEIGHTS="weights fetch skipped (ENGRAM_SKIP_WEIGHTS_FETCH=1); hashing fallback"
elif [ "$EMBEDDINGS_SYNCED" = "0" ]; then
    WEIGHTS="hashing fallback (no onnxruntime)"
else
    if (cd "$SERVER_DIR" && timeout 180 uv run --with huggingface_hub \
            python scripts/fetch-embedding-model.py >/dev/null 2>&1); then
        WEIGHTS="weights fetched (MiniLM ONNX)"
    else
        WEIGHTS="weights unavailable (network policy?); hashing fallback — vault_status reports the active backend"
    fi
fi

say "$DEPS · $MANIFEST · $WEIGHTS"

# 4. stdio smoke test (stdlib-only client)
SMOKE_OUT="$(cd "$SERVER_DIR" && python3 scripts/stdio-smoke.py --timeout 120 2>&1)"
if [ $? -eq 0 ]; then
    say "$(printf '%s\n' "$SMOKE_OUT" | tail -1)"
else
    printf '%s\n' "$SMOKE_OUT" | tail -12
    say "smoke test FAILED — rerun: cd $SERVER_DIR && python3 scripts/stdio-smoke.py"
fi

exit 0
