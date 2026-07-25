#!/usr/bin/env bash
# SessionEnd: append session end record
HIVE_ROOT="${HIVE_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/hive}}"
echo "SESSION_END $(date -Iseconds) | $(pwd) | reason=$CLAUDE_SESSION_END_REASON" >> "$HIVE_ROOT/_meta/session-end.log"
