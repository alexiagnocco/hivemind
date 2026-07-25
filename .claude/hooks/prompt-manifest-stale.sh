#!/usr/bin/env bash
# UserPromptSubmit: nudge if the hive manifest is stale (>3 days)
HIVE_ROOT="${HIVE_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/hive}}"
MANIFEST="$HIVE_ROOT/_meta/hive-manifest.json"
SENTINEL=/tmp/hive-manifest-warned
if [ -f "$MANIFEST" ] && [ ! -f "$SENTINEL" ]; then
  STALE=$(find "$MANIFEST" -mtime +3 2>/dev/null)
  if [ -n "$STALE" ]; then
    echo "Nudge: Hive manifest is stale (>3 days) — retrieval quality degrades. Rebuild it (hive_rebuild tool, or python _meta/scripts/build-manifest.py)."
    touch "$SENTINEL"
  fi
fi
