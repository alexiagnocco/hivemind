#!/usr/bin/env bash
# UserPromptSubmit: nudge if the vault manifest is stale (>3 days)
VAULT_ROOT="${VAULT_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/vault}}"
MANIFEST="$VAULT_ROOT/_meta/vault-manifest.json"
SENTINEL=/tmp/vault-manifest-warned
if [ -f "$MANIFEST" ] && [ ! -f "$SENTINEL" ]; then
  STALE=$(find "$MANIFEST" -mtime +3 2>/dev/null)
  if [ -n "$STALE" ]; then
    echo "Nudge: Vault manifest is stale (>3 days) — retrieval quality degrades. Rebuild it (vault_rebuild tool, or python _meta/scripts/build-manifest.py)."
    touch "$SENTINEL"
  fi
fi
