#!/usr/bin/env bash
# Stop: remind to sync the hive if file operations happened this session
INPUT="$(cat)"
STOP_HOOK_ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0
HIVE_ROOT="${HIVE_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/hive}}"
SESSION_LOG="$HIVE_ROOT/_meta/session-activity.log"
if [ -s "$SESSION_LOG" ]; then
  LAST_MARKER=$(grep -n '^--- SESSION' "$SESSION_LOG" | tail -1 | cut -d: -f1 || echo 0)
  TOTAL=$(wc -l < "$SESSION_LOG")
  CHANGES=$((TOTAL - ${LAST_MARKER:-0}))
  if [ "$CHANGES" -gt 0 ]; then
    PROJECT=$(basename "$(pwd)")
    NEW_MD=$(tail -n "$CHANGES" "$SESSION_LOG" | grep -v '^---' | grep -cE '\.md$' 2>/dev/null || echo 0)
    echo "HIVE SYNC REQUIRED: $CHANGES file operations this session."
    echo "Update memory/projects/$PROJECT.md with decisions, milestones, or learnings."
    if [ "$NEW_MD" -gt 2 ]; then
      echo "$NEW_MD notes touched this session — consider /handoff to capture session context."
    fi
    echo "If nothing hive-worthy happened, acknowledge explicitly."
  fi
fi
