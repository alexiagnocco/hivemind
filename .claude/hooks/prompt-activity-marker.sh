#!/usr/bin/env bash
# UserPromptSubmit: mark session activity boundary
HIVE_ROOT="${HIVE_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/hive}}"
echo "--- SESSION $(date -Iseconds) | $(pwd) ---" >> "$HIVE_ROOT/_meta/session-activity.log"
