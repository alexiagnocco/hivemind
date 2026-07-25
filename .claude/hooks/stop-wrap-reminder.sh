#!/usr/bin/env bash
# Stop: suggest /wrap if substantive work was done
INPUT="$(cat)"
STOP_HOOK_ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0
HIVE_ROOT="${HIVE_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/hive}}"
SESSION_LOG="$HIVE_ROOT/_meta/session-activity.log"
if [ -s "$SESSION_LOG" ]; then
  LAST_MARKER=$(grep -n '^--- SESSION' "$SESSION_LOG" | tail -1 | cut -d: -f1 || echo 0)
  TOTAL=$(wc -l < "$SESSION_LOG")
  CHANGES=$((TOTAL - ${LAST_MARKER:-0}))
  if [ "$CHANGES" -gt 3 ]; then
    echo "SESSION END: Run /wrap for graceful shutdown (retro + feedback + handoff). Or individually: /retro, /feedback, /handoff."
  fi
fi
